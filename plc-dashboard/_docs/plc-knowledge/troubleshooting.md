# PLC監視システム トラブルシューティングガイド

**作成日:** 2025-10-24
**最終更新:** 2026-01-24

## 概要

PLC監視システムでよくある問題と解決策を記録します。

## 目次

1. [PLC通信エラー](#plc通信エラー)
2. [中央サーバー通信エラー](#中央サーバー通信エラー)
3. [データが表示されない](#データが表示されない)
4. [設備が見つからない](#設備が見つからない)
5. [Socket.IO Greenletエラー](#socketio-greenletエラー)
6. [ラズパイデプロイ問題](#ラズパイデプロイ問題)

---

## PLC通信エラー

### 症状

```
ERROR - PLC通信エラー: [Errno 111] Connection refused
ERROR - PLC通信タイムアウト
```

### 原因と解決策

#### 1. PLCのIPアドレスが間違っている

**確認方法:**
```bash
# PLCにpingが通るか確認
ping 192.168.0.10
```

**解決策:**
- PLCの設定画面でIPアドレスを確認
- `.env`ファイルの`PLC_IP`を修正

```bash
# plc-dashboard/raspi_agent/.env
PLC_IP=192.168.0.10  # 正しいIPアドレスに修正
```

#### 2. ポート番号が間違っている

**デフォルトポート:**
| メーカー | プロトコル | ポート |
|---------|-----------|-------|
| キーエンス | Modbus TCP | 502 |
| オムロン | FINS | 9600 |
| 三菱電機 | MC Protocol | 5000 |

**確認方法:**
```bash
# ポートが開いているか確認
nc -zv 192.168.0.10 502
```

**解決策:**
```bash
# plc-dashboard/raspi_agent/.env
PLC_PORT=502  # 正しいポート番号に修正
```

#### 3. PLCのEthernet通信設定が無効

**解決策:**
- PLCの設定でEthernet通信を有効化
- ファイアウォール設定を確認
- PLC側のIPアドレス設定を確認

#### 4. ケーブル断線・スイッチ故障

**確認方法:**
```bash
# ネットワークインターフェースの状態確認
ip link show eth0

# ルーティングテーブル確認
ip route
```

**解決策:**
- LANケーブルを交換
- スイッチのポートを変更
- ラズパイを再起動

#### 5. タイムアウト時間が短すぎる

**確認箇所:**
`plc-dashboard/raspi_agent/plc_drivers/*.py`

**解決策:**
```python
# タイムアウトを3-5秒に設定
plc.connect(ip, port, timeout=5.0)
```

詳細は `_docs/plc-knowledge/timeout-settings.md` を参照。

---

## 中央サーバー通信エラー

### 症状

```
WARNING - 中央サーバー通信タイムアウト、ローカルバッファに保存
ERROR - 送信エラー: HTTPConnectionPool(host='192.168.1.10', port=5000)
```

### 原因と解決策

#### 1. 中央サーバーが起動していない

**確認方法:**
```bash
# 中央サーバー側で確認
cd plc-dashboard/backend
flask --app manage.py run
```

**解決策:**
中央サーバーを起動する。

```bash
# Docker Composeで起動
cd plc-dashboard
docker compose up -d backend
```

#### 2. 中央サーバーのIPアドレスが間違っている

**確認方法:**
```bash
# 中央サーバーにpingが通るか確認
ping 192.168.1.10
```

**解決策:**
```bash
# plc-dashboard/raspi_agent/.env
CENTRAL_SERVER_IP=192.168.1.10  # 正しいIPアドレスに修正
CENTRAL_SERVER_PORT=5000
```

#### 3. ファイアウォールでブロックされている

**確認方法:**
```bash
# ポートが開いているか確認
nc -zv 192.168.1.10 5000
```

**解決策:**
中央サーバー側でファイアウォールを設定。

```bash
# Windows Defender Firewall
# ポート5000を許可

# Linux (ufw)
sudo ufw allow 5000/tcp
```

#### 4. ローカルバッファが満杯

**確認方法:**
```python
# plc-dashboard/raspi_agent/db_utils.py
db_api = DatabaseAPI()
db_api.get_buffer_stats()  # バッファ統計を表示
```

**解決策:**
古いバッファデータをクリーンアップ。

```bash
# 7日以上前のデータを削除
python -c "from db_utils import DatabaseAPI; db_api = DatabaseAPI(); db_api.cleanup_buffer()"
```

---

## データが表示されない

### 症状

- モニタリング画面にデータが表示されない
- グラフが空白
- 「データがありません」と表示

### 原因と解決策

#### 1. PLCデータが送信されていない

**確認方法:**
```bash
# Raspberry Pi側のログ確認
tail -f plc-dashboard/raspi_agent/plc_agent.log

# 以下のログが出力されているか確認
# "📤 データ送信成功"
```

**解決策:**
- PLCエージェントを再起動
- PLC通信エラーを確認（前述）

#### 2. WebSocket接続が切れている

**確認方法:**
ブラウザの開発者コンソールで確認。

```
WebSocket connection to 'ws://localhost:5000/socket.io/' failed
```

**解決策:**
ページをリロード、または中央サーバーを再起動。

#### 3. データベースに保存されていない

**確認方法:**
```bash
# 中央サーバー側で確認
cd plc-dashboard/backend
python scripts/check_data.py
```

**解決策:**
- データベース接続を確認
- マイグレーションを実行

```bash
cd plc-dashboard/backend
flask --app manage.py db upgrade
```

#### 4. 期間指定が間違っている

**確認方法:**
モニタリング画面のURL確認。

```
http://localhost:3000/monitoring/DEMO_001?period=24h
```

**解決策:**
期間を変更して再確認。

- `1h`: 直近1時間
- `6h`: 直近6時間
- `24h`: 直近24時間
- `7d`: 直近7日間
- `30d`: 直近30日間

---

## 設備が見つからない

### 症状

```
ERROR - 設備が見つかりません: DEMO_001
```

### 原因と解決策

#### 1. 設備が登録されていない

**確認方法:**
```bash
# 中央サーバーで設備一覧を取得
curl http://localhost:5000/api/equipment
```

**解決策:**
Raspberry Pi側で初期設定画面から設備を登録。

```
http://<ラズパイIP>:8080/setup
```

#### 2. CPUシリアル番号が一致しない

**確認方法:**
```bash
# Raspberry Pi側でCPUシリアル番号を確認
python plc-dashboard/raspi_agent/test_cpu_serial.py
```

**解決策:**
中央サーバーで設備検索。

```bash
curl "http://localhost:5000/api/equipment/search?cpu_serial_number=<シリアル番号>"
```

設備が見つかれば、`equipment_id`を確認して`.env`に設定。

#### 3. 設備IDの優先順位問題

**設備識別の優先順位:**
1. `cpu_serial_number`（最優先）
2. `mac_address`
3. `equipment_id`

**解決策:**
`plc-dashboard/backend/api/routes.py:388-432` の設備登録ロジックを確認。

必ず`cpu_serial_number`で検索してから`equipment_id`を更新する。

---

## Socket.IO Greenletエラー

### 症状

```
RuntimeError: greenlet_spawn has not been called; cannot call await_()
```

### 原因

Socket.IOのデフォルトモード（`eventlet`）とFlaskの非同期処理が競合。

### 解決策

Socket.IOを`threading`モードで初期化する。

**実装箇所:**
`plc-dashboard/backend/app.py:45-46`

```python
# ✅ 正しい: threadingモードで初期化
socketio.init_app(app, async_mode='threading', cors_allowed_origins="*")
```

**間違った例:**
```python
# ❌ 間違い: デフォルトモード（eventlet）
socketio.init_app(app, cors_allowed_origins="*")
```

詳細は `_docs/decisions/socketio-threading-mode.md` を参照。

---

## ラズパイデプロイ問題

### 症状

```
bash: scp_bulk_push.sh: Permission denied
ERROR: Cannot connect to Raspberry Pi: 192.168.0.101
```

### 原因と解決策

#### 1. スクリプトに実行権限がない

**解決策:**
```bash
chmod +x plc-dashboard/raspi_agent/scp_bulk_push.sh
```

#### 2. SSH鍵認証が設定されていない

**確認方法:**
```bash
# ラズパイにSSHできるか確認
ssh pi@192.168.0.101
```

**解決策:**
SSH鍵を設定する。

```bash
# SSH鍵生成（初回のみ）
ssh-keygen -t rsa

# 公開鍵をラズパイにコピー
ssh-copy-id pi@192.168.0.101
```

#### 3. ip_list.csvが正しくない

**確認方法:**
```bash
cat plc-dashboard/raspi_agent/ip_list.csv
```

**正しいフォーマット:**
```csv
ip_address
192.168.0.101
192.168.0.102
```

**解決策:**
カンマ区切りではなく、改行区切りで記載。

#### 4. systemdサービスが起動しない

**確認方法:**
```bash
# ラズパイにSSH接続
ssh pi@192.168.0.101

# サービス状態確認
sudo systemctl status plc_ui.service
```

**解決策:**
ログを確認して原因を特定。

```bash
# ログ確認
sudo journalctl -u plc_ui.service -n 50
```

---

## デバッグツール

### 1. ログレベル変更

```bash
# plc-dashboard/raspi_agent/.env
LOG_LEVEL=DEBUG  # INFO, WARNING, ERROR, CRITICAL
```

### 2. ダミーモードで動作確認

```bash
# plc-dashboard/raspi_agent/.env
USE_DUMMY_PLC=true
```

### 3. データベース接続テスト

```bash
cd plc-dashboard
python scripts/test_db_connection.py
```

### 4. ネットワーク診断

```bash
# PLCへの疎通確認
ping 192.168.0.10

# ポート開放確認
nc -zv 192.168.0.10 502

# ルーティング確認
traceroute 192.168.0.10

# パケットキャプチャ
sudo tcpdump -i eth0 host 192.168.0.10
```

### 5. バッファ統計確認

```python
from db_utils import DatabaseAPI
db_api = DatabaseAPI()
db_api.get_buffer_stats()
```

---

## よくある質問（FAQ）

### Q1: ダミーモードで動作するのに、実PLCで動作しない

**A1:** PLC通信設定を確認してください。
- IPアドレス、ポート番号
- PLCのEthernet通信設定
- ファイアウォール設定

詳細は「PLC通信エラー」セクションを参照。

### Q2: データが途切れ途切れにしか表示されない

**A2:** 通信タイムアウトやネットワーク不安定が原因です。
- ローカルバッファ統計を確認
- ネットワーク診断を実行
- タイムアウト値を見直す

詳細は `_docs/plc-knowledge/timeout-settings.md` を参照。

### Q3: Raspberry Piが再起動すると設備IDが変わる

**A3:** 設備識別は`cpu_serial_number`を優先してください。
- `cpu_serial_number`は不変
- `equipment_id`は可変（ユーザー定義）
- 設備登録ロジックを確認

詳細は `_docs/decisions/equipment-identification-strategy.md` を参照。

### Q4: 古いデータが削除されない

**A4:** スケジューラーが動作していません。
- `plc-dashboard/backend/api/scheduler.py`を確認
- 手動でクリーンアップを実行

```bash
cd plc-dashboard/backend
python log_manager.py cleanup --days 90
```

---

## 関連ドキュメント

- `plc-dashboard/_docs/plc-knowledge/protocols.md` - PLCプロトコル実装ガイド
- `plc-dashboard/_docs/plc-knowledge/endianness.md` - エンディアン問題
- `plc-dashboard/_docs/plc-knowledge/timeout-settings.md` - タイムアウト設定
- `plc-dashboard/_docs/architecture/raspi-agent.md` - ローカルバッファリング機能（local_buffer.pyセクション）
- `plc-dashboard/_docs/decisions/socketio-threading-mode.md` - Socket.IO設定

---

**最終更新:** 2026-01-19
