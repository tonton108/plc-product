# タイムアウト設定のベストプラクティス

**作成日:** 2025-10-24
**最終更新:** 2026-01-24

## 概要

PLC通信におけるタイムアウト設定の考え方とベストプラクティスを記録します。

## なぜタイムアウトが重要か

PLC通信は工場LANを経由するため、以下のリスクがあります：
1. **ネットワーク障害**: ケーブル断線、スイッチ故障
2. **PLC側の問題**: PLCの高負荷、プログラム停止
3. **通信輻輳**: 他の機器との通信競合

**タイムアウト未設定のリスク:**
- アプリケーションが無限に待機（ハングアップ）
- Raspberry Piの監視スレッドが停止
- 他の設備監視が停止
- システム全体の信頼性低下

## 推奨タイムアウト値

### 通信タイムアウト: 3-5秒

```python
# ✅ 推奨: 3-5秒のタイムアウト
plc.connect(ip="192.168.0.10", port=5000, timeout=5.0)
```

**根拠:**
- 通常のPLC応答時間: 50-200ms
- ネットワーク遅延: 10-50ms
- リトライ余裕: 3-5秒あれば2-3回リトライ可能
- これ以上待っても復旧可能性は低い

### データ収集間隔: 1-5秒

```python
# plc-dashboard/raspi_agent/plc_agent.py
LOG_INTERVAL_MS = int(os.getenv('LOG_INTERVAL_MS', '5000'))  # デフォルト5秒
```

**根拠:**
- リアルタイム性とサーバー負荷のバランス
- 1秒以下: 高頻度更新が必要な監視（温度、圧力）
- 5秒: 一般的な設備監視
- 10秒以上: 低頻度監視（日報、集計）

### 再接続リトライ: 3回まで

```python
# plc-dashboard/raspi_agent/plc_agent.py:1193-1211
MAX_RETRY = 3
retry_count = 0

while retry_count < MAX_RETRY:
    try:
        data = read_from_plc(config)
        if data:
            break  # 成功
    except Exception as e:
        retry_count += 1
        if retry_count >= MAX_RETRY:
            logger.error(f"最大リトライ回数に到達: {e}")
            # ダミーモードにフォールバック
            data = generate_dummy_data(data_points)
        else:
            time.sleep(1)  # 1秒待機してリトライ
```

**根拠:**
- 1回目の失敗: 一時的な通信エラーの可能性
- 2回目の失敗: ネットワーク問題の可能性
- 3回目の失敗: PLC側の問題、ダミーモードに切り替え

## プロトコル別タイムアウト設定

### キーエンス（Modbus TCP）

```python
# plc-dashboard/raspi_agent/plc_drivers/keyence.py
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient(
    host=config['plc_ip'],
    port=config.get('plc_port', 502),
    timeout=5.0  # ✅ タイムアウト5秒
)
```

### オムロン（FINS）

```python
# plc-dashboard/raspi_agent/plc_drivers/omron.py
from fins.udp import UDPFinsConnection

conn = UDPFinsConnection()
conn.connect(config['plc_ip'])
conn.timeout = 5.0  # ✅ タイムアウト5秒
```

### 三菱電機（MC Protocol）

```python
# plc-dashboard/raspi_agent/plc_drivers/mitsubishi.py
import pymcprotocol

plc = pymcprotocol.Type3E()
plc.connect(
    ip=config['plc_ip'],
    port=config.get('plc_port', 5000),
    timeout=5.0  # ✅ タイムアウト5秒
)
```

## よくある間違い

### 間違い1: タイムアウト未設定

```python
# ❌ 間違い: タイムアウトなし
plc.connect(ip, port)
# → ネットワーク障害時に無限待機
```

**問題:**
- デフォルトタイムアウトはライブラリ依存（30秒、60秒、無限など）
- 長時間ハングアップのリスク

**修正:**
```python
# ✅ 正しい: 必ずタイムアウトを明示
plc.connect(ip, port, timeout=5.0)
```

### 間違い2: タイムアウトが短すぎる

```python
# ❌ 間違い: タイムアウト1秒未満
plc.connect(ip, port, timeout=0.5)
# → 通常のネットワーク遅延でもタイムアウトする
```

**問題:**
- 工場LANは必ずしも高速ではない（100Mbps、スイッチ経由）
- 他の機器との通信競合でパケットロスあり

**修正:**
```python
# ✅ 正しい: 余裕を持ったタイムアウト
plc.connect(ip, port, timeout=3.0)  # 最低3秒
```

### 間違い3: タイムアウトが長すぎる

```python
# ❌ 間違い: タイムアウト30秒以上
plc.connect(ip, port, timeout=30.0)
# → 障害検出が遅れ、システム全体に影響
```

**問題:**
- 30秒間ハングアップすると、他の設備監視も停止
- ユーザーに「システムが動いていない」と誤解される

**修正:**
```python
# ✅ 正しい: 適切なタイムアウト
plc.connect(ip, port, timeout=5.0)  # 5秒で諦めて次へ
```

## エラーハンドリング

タイムアウトエラーは必ず`try-except`でキャッチします。

```python
import socket

try:
    plc.connect(ip, port, timeout=5.0)
    data = plc.read_data(address, count)
except socket.timeout:
    logger.error(f"PLC通信タイムアウト: {ip}:{port}")
    # フォールバック処理
    return None
except Exception as e:
    logger.error(f"PLC通信エラー: {e}")
    return None
```

## ローカルバッファリングとの連携

タイムアウト時は、ローカルバッファに未送信データを保存します。

```python
# plc-dashboard/raspi_agent/db_utils.py:211-224
def send_log_data(self, log_data):
    """
    ログデータを送信（タイムアウト時はローカルバッファに保存）
    """
    try:
        response = requests.post(
            url,
            json=log_data,
            timeout=5.0  # ✅ HTTPタイムアウト5秒
        )
        if response.status_code == 200:
            return True
    except requests.exceptions.Timeout:
        logger.warning("中央サーバー通信タイムアウト、ローカルバッファに保存")
        self.local_buffer.save(equipment_id, log_data)
        return False
    except Exception as e:
        logger.error(f"送信エラー: {e}")
        self.local_buffer.save(equipment_id, log_data)
        return False
```

## Codexレビュー観点

`.github/workflows/codex-review.yml:36` でタイムアウト設定を自動チェックしています：

```yaml
- Error handling and timeout settings
```

Codexは以下のコードを指摘します：
- `plc.connect(ip, port)` ← タイムアウト未指定
- `timeout=0.5` ← タイムアウトが短すぎる
- `timeout=60.0` ← タイムアウトが長すぎる
- `try-except`なし ← エラーハンドリング不足

## デバッグ方法

### 1. ログでタイムアウトを確認

```python
import time

start_time = time.time()
try:
    plc.connect(ip, port, timeout=5.0)
    data = plc.read_data(address, count)
    elapsed = time.time() - start_time
    logger.info(f"PLC通信成功: {elapsed:.3f}秒")
except socket.timeout:
    elapsed = time.time() - start_time
    logger.error(f"PLC通信タイムアウト: {elapsed:.3f}秒")
```

### 2. ネットワーク診断

```bash
# PLC疎通確認
ping 192.168.0.10

# ポート開放確認
nc -zv 192.168.0.10 502

# パケットキャプチャ
sudo tcpdump -i eth0 host 192.168.0.10
```

### 3. タイムアウト統計

```python
# plc-dashboard/raspi_agent/plc_agent.py
timeout_count = 0
success_count = 0

# 統計情報をログ出力
logger.info(f"通信統計: 成功={success_count}, タイムアウト={timeout_count}")
```

## チェックリスト

PLC通信実装時は、以下を確認してください：

- [ ] すべてのPLC接続で`timeout`パラメータを明示しているか
- [ ] タイムアウト値は3-5秒の範囲か
- [ ] タイムアウトエラーを`try-except`でキャッチしているか
- [ ] タイムアウト時のフォールバック処理があるか
- [ ] ローカルバッファにデータを保存しているか
- [ ] ログでタイムアウト発生を記録しているか

## 関連ドキュメント

- `plc-dashboard/_docs/plc-knowledge/protocols.md` - PLCプロトコル実装ガイド
- `plc-dashboard/_docs/plc-knowledge/troubleshooting.md` - トラブルシューティングガイド
- `plc-dashboard/_docs/architecture/raspi-agent.md` - ローカルバッファリング機能（local_buffer.pyセクション）

---

**参考リンク:**
- [Python socket — Low-level networking interface](https://docs.python.org/3/library/socket.html#socket.socket.settimeout)
- [Requests — Timeouts](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts)
