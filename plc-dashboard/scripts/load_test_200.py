"""200台スケール負荷検証スクリプト（Phase 3）

200設備を登録し、同時POSTでログを投入して、スケール施策
（設備別room配信・logsの月次パーティション・DROPクリーンアップ）が
200台規模の負荷で正しく動くことを確認する。

主眼（何を見るか）:
- 登録・ログPOSTのエラー率／デッドロックの有無
- ログが当月パーティションへ正しくルーティングされること（DB側で確認）
- 大量データでのクリーンアップ（古い月DROP＋境界DELETE）が高速に動くこと
- 読み取り（latest/history）のレイテンシ傾向

注意:
- compose の backend は `flask run`（開発サーバ）のため、**絶対スループットは
  本番のWaitress/WSGIを反映しない**。本番構成の負荷検証はPhase 4の別ゲート。
- 事前に `flask auth seed` でadminと共有APIキーを作成しておくこと（下記の既定値）。

使い方:
    # 事前準備（例）
    docker compose up -d db backend
    docker exec plc-backend flask --app manage.py auth seed \
        --admin-password admin123! --api-key e2e-shared-key-123456
    python scripts/load_test_200.py

    # DB側の検証（別途）
    docker exec plc-db psql -U plc_user -d plc_monitor -c \
      "SELECT c.relname, count(*) FROM logs l JOIN pg_class c ON c.oid=l.tableoid GROUP BY 1 ORDER BY 1;"

環境変数で調整可能: BASE_URL, API_KEY, ADMIN_PASSWORD, N_EQUIP, LOGS_PER_EQUIP, POST_WORKERS
"""
import json
import os
import time
import statistics
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = os.getenv("BASE_URL", "http://localhost:5000")
API_KEY = os.getenv("API_KEY", "e2e-shared-key-123456")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123!")
N_EQUIP = int(os.getenv("N_EQUIP", "200"))
LOGS_PER_EQUIP = int(os.getenv("LOGS_PER_EQUIP", "25"))
POST_WORKERS = int(os.getenv("POST_WORKERS", "32"))
REGISTER_WORKERS = int(os.getenv("REGISTER_WORKERS", "32"))


def _req(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
            return resp.status, (time.perf_counter() - t0)
    except urllib.error.HTTPError as e:
        return e.code, (time.perf_counter() - t0)
    except Exception:
        return -1, (time.perf_counter() - t0)


def login():
    data = json.dumps({"username": "admin", "password": ADMIN_PASSWORD}).encode()
    req = urllib.request.Request(
        BASE + "/api/auth/login", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["token"]


def register_one(i):
    body = {
        "equipment_id": f"LOAD_{i:04d}",
        "manufacturer": "Mitsubishi",
        "series": "iQ-R",
        "plc_ip": "192.168.1.%d" % (i % 254 + 1),
        "mac_address": "02:00:00:%02X:%02X:%02X" % (i >> 16 & 255, i >> 8 & 255, i & 255),
        "cpu_serial_number": f"CPU_LOAD_{i:04d}",
        "port": 502,
        "interval": 5000,
    }
    return _req("POST", "/api/register", body, {"X-API-Key": API_KEY})[0]


def post_log(args):
    i, seq = args
    body = {
        "equipment_id": f"LOAD_{i:04d}",
        "temperature": 20.0 + (seq % 50) * 0.1,
        "production_count": seq,
        "sensor_a": seq * 1.5,  # 動的項目（Phase 2）
    }
    return _req("POST", "/api/logs", body, {"X-API-Key": API_KEY})


def summarize(name, results):
    codes = {}
    lat = []
    for status, dt in results:
        codes[status] = codes.get(status, 0) + 1
        lat.append(dt)
    lat.sort()
    p50 = statistics.median(lat)
    p95 = lat[int(len(lat) * 0.95)] if lat else 0
    p99 = lat[int(len(lat) * 0.99)] if lat else 0
    print(f"[{name}] codes={codes} "
          f"p50={p50*1000:.0f}ms p95={p95*1000:.0f}ms p99={p99*1000:.0f}ms")
    return codes


def main():
    total = N_EQUIP * LOGS_PER_EQUIP
    print(f"=== 200台負荷検証: {N_EQUIP}設備 x {LOGS_PER_EQUIP}ログ = {total} POST ===")

    # 1. 設備登録
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=REGISTER_WORKERS) as ex:
        reg = list(ex.map(register_one, range(N_EQUIP)))
    reg_ok = sum(1 for c in reg if c == 200)
    print(f"[登録] {reg_ok}/{N_EQUIP} 成功  所要 {time.perf_counter()-t0:.1f}s")

    # 2. ログ投入（同時負荷）
    tasks = [(i, seq) for seq in range(LOGS_PER_EQUIP) for i in range(N_EQUIP)]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=POST_WORKERS) as ex:
        results = list(ex.map(post_log, tasks))
    elapsed = time.perf_counter() - t0
    codes = summarize("ログPOST", results)
    ok = codes.get(200, 0)
    print(f"[ログPOST] {ok}/{len(tasks)} 成功  {elapsed:.1f}s  "
          f"スループット {ok/elapsed:.0f} req/s （※開発サーバ値）")

    # 3. 読み取りレイテンシ（サンプル設備）
    token = login()
    auth = {"Authorization": f"Bearer {token}"}
    step = max(1, N_EQUIP // 10)
    lat_latest = [
        _req("GET", f"/api/logs/LOAD_{i:04d}/latest", None, auth)[1]
        for i in range(0, N_EQUIP, step)
    ]
    lat_hist = [
        _req("GET", f"/api/logs/LOAD_{i:04d}/history?limit=100", None, auth)[1]
        for i in range(0, N_EQUIP, step)
    ]
    print(f"[読取] latest p50={statistics.median(lat_latest)*1000:.0f}ms  "
          f"history(100) p50={statistics.median(lat_hist)*1000:.0f}ms")

    if ok != len(tasks) or reg_ok != N_EQUIP:
        print("!! 一部リクエストが失敗しました。バックエンドログを確認してください")
    print("=== 完了。DB側の配置検証は上部docstringのpsql例を参照 ===")


if __name__ == "__main__":
    main()
