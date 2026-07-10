"""7d/30d集計ビューの動的項目表示テスト（Issue #14 の回帰確認）

設備詳細ページ（/equipment/<id>）で期間を7dに切り替えたとき、日次集計の
動的項目（<項目名>_avg）がチャート/CSVに反映されることをPlaywrightで確認する。

## 前提データ（このスクリプトは検証のみ・データ投入はしない）
1. 認証: `flask auth seed --admin-password admin123! --api-key <key>`
2. 設備 TEST_VIEW を登録し、動的項目 sensor_x を有効化したPLC設定を保存
3. TEST_VIEW の日次集計を投入（data_summaryに sensor_x_avg を含む、7d以内の日付）
   例:
     INSERT INTO daily_log_summaries (equipment_id,date,data_count,temperature_avg,data_summary)
     VALUES (<id>, (now()-interval '1 day')::date, 100, 24.5,
             '{"sensor_x_avg":42.5,"sensor_x_max":50,"sensor_x_min":30}'::json);

## 実行
    pip install playwright && python -m playwright install chromium
    python scripts/test_aggregation_view.py

期待: 7d切替後、チャートが描画され（canvas存在）、CSVに sensor_x_avg の値が出る。
"""
import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
API = "http://127.0.0.1:5000"
EQUIP = "TEST_VIEW"
EXPECT_VALUES = ["42.5", "44"]  # 投入した sensor_x_avg


def get_token():
    d = json.dumps({"username": "admin", "password": "admin123!"}).encode()
    r = urllib.request.Request(API + "/api/auth/login", data=d,
                               headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(r).read())["token"]


def main():
    token = get_token()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        ctx.add_init_script(
            f"localStorage.setItem('plc_auth_token', {json.dumps(token)});"
            "localStorage.setItem('plc_auth_user', '{\"username\":\"admin\",\"role\":\"admin\"}');"
        )
        page = ctx.new_page()
        page.goto(f"{FRONTEND}/equipment/{EQUIP}", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # 期間を7d（日次集計）に切替
        page.get_by_role("button", name="7日").click()
        page.wait_for_timeout(2500)

        canvas = page.locator("canvas").count()

        with page.expect_download() as dl_info:
            page.locator("button:has(.mdi-download)").click()
        csv = open(dl_info.value.path(), encoding="utf-8").read()

        has_values = all(v in csv for v in EXPECT_VALUES)
        ok = canvas >= 1 and has_values
        print("canvas:", canvas, " CSVに集計値:", has_values)
        print("CSV先頭:\n" + csv[:200])
        print("RESULT:", "PASS" if ok else "FAIL")
        browser.close()
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
