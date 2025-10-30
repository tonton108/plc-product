# テストとデバッグガイド

**作成日:** 2025-10-30
**最終更新:** 2025-10-30

## デモデータ送信

### 実行順序

**重要:** 以下の順序で起動してください。

```bash
# 1. バックエンド起動
cd plc-dashboard/backend
flask --app manage.py run

# 2. フロントエンド起動（別ターミナル）
cd plc-dashboard
npm run dev

# 3. デモデータ送信開始（別ターミナル）
cd plc-dashboard/backend
python demo_data_sender.py --mode continuous --interval 2.0

# 4. ブラウザで確認
# http://localhost:3000/monitoring/DEMO_001
```

### デモツールの使い方

#### 継続的なデータ送信

```bash
# 2秒間隔で連続送信
python demo_data_sender.py --mode continuous --interval 2.0

# 5秒間隔で連続送信
python demo_data_sender.py --mode continuous --interval 5.0
```

#### 単発データ送信

```bash
# 1回だけデータを送信
python demo_data_sender.py --mode single
```

#### 設備登録のみ

```bash
# 設備情報のみ登録（データは送信しない）
python demo_data_sender.py --mode register --equipment-id DEMO_001
```

## ログの確認

### Flask側のログ

**重要なログメッセージ:**

```
📥 PLCデータ受信: DEMO_001
  - timestamp: 2025-01-15T10:30:00
  - data: {'temperature': 25.5, 'pressure': 101.3}

📡 WebSocket送信完了
  - room: monitoring
  - equipment_id: DEMO_001

🔌 abc123def456 joined monitoring for DEMO_001
```

**ログ確認コマンド:**

```bash
# Docker環境の場合
docker compose logs -f backend

# 開発環境の場合
# ターミナルに直接出力されます
```

### Nuxt側のログ

ブラウザの開発者コンソール（F12）で確認：

```javascript
✅ WebSocket接続成功
📊 データ更新: {equipment_id: 'DEMO_001', timestamp: '2025-01-15T10:30:00', ...}
🔄 グラフ更新完了
```

### Socket.IOイベントの確認

**Chrome DevTools:**
1. F12で開発者ツールを開く
2. Network タブ → WS（WebSocket）を選択
3. Socket.IO接続を選択
4. Messages タブでイベントを確認

## トラブルシューティング

### データベース接続エラー

#### 症状

```
sqlalchemy.exc.OperationalError: could not connect to server
```

#### 原因

- PostgreSQLが起動していない
- 環境変数`DATABASE_URL`が正しくない
- ファイアウォールでポート5432がブロックされている

#### 解決方法

```bash
# PostgreSQL接続確認
psql -U plc_user -h localhost -d plc_monitor -c "SELECT version();"

# PostgreSQLの起動状態確認
# Dockerの場合
docker compose ps db

# データベース存在確認
sudo -u postgres psql -l

# マイグレーション実行
cd backend
flask --app manage.py db upgrade
```

### Alembicマイグレーション履歴の不整合

#### 症状

```
alembic.util.exc.CommandError: Can't locate revision identified by 'XXXXX'
```

#### 原因

PostgreSQLの`alembic_version`テーブルの値が、migrationsディレクトリ内の最新リビジョンと一致していない

#### 解決方法

```bash
# 1. 最新のマイグレーションファイルを確認
ls -lt backend/migrations/versions/ | head -5
grep "revision = " backend/migrations/versions/*.py | tail -3

# 2. alembic_versionテーブルの現在値を確認
psql -U plc_user -h localhost -d plc_monitor -c "SELECT * FROM alembic_version;"

# 3. 最新リビジョンに更新（例：31ebb7e53291）
psql -U plc_user -h localhost -d plc_monitor -c "UPDATE alembic_version SET version_num = '31ebb7e53291';"

# 4. マイグレーション再実行
cd backend
flask --app manage.py db upgrade
```

### 設備が登録されない・ローカル設定と表示される

#### 症状

初回設定画面で設備を登録したが、モニタリング画面に「ローカル設定」と表示され、中央サーバーに登録されていない

#### 原因

ローカルの`plc_config.json`に設備情報が保存されているが、中央サーバーには登録されていない

#### 解決方法

```bash
# 1. ラズパイエージェントを停止
lsof -ti :5001 | xargs kill -9

# 2. ローカル設定をクリア（バックアップ作成）
cd raspi_agent
cp config/plc_config.json config/plc_config.json.backup
echo '{}' > config/plc_config.json

# 3. ラズパイエージェントを再起動
python3 agent_app.py

# 4. ブラウザで http://localhost:5001/ にアクセスし、初回設定画面から再登録
```

### Socket.IO接続エラー

#### 症状

```
WebSocket connection to 'ws://localhost:5000' failed
```

#### 原因

- バックエンドが起動していない
- CORSオリジン設定が正しくない
- ポート5000が使用中

#### 解決方法

```bash
# バックエンドの起動確認
lsof -i :5000

# CORSオリジン設定を確認
# backend/app.py:18-20, 60
grep -n "CORS_ORIGINS" backend/app.py

# ポート5000を使用しているプロセスを確認
lsof -i :5000

# プロセスを停止
kill -9 <PID>
```

### データが表示されない

#### 確認手順

1. **データが保存されているか確認**

```bash
# REST APIで最新データを取得
curl http://localhost:5000/api/logs/DEMO_001/latest
```

2. **Socket.IOイベントが受信されているか確認**

ブラウザコンソール（F12）で以下を実行：

```javascript
// Socket.IO接続状態を確認
console.log(socket.connected)  // true が期待値

// イベントリスナーを確認
socket.onAny((eventName, ...args) => {
  console.log('受信イベント:', eventName, args)
})
```

3. **Flaskログでデータ受信・配信を確認**

```bash
docker compose logs -f backend | grep "📡 WebSocket"
```

### グラフが更新されない

#### 症状

モニタリング画面でグラフが表示されるが、リアルタイム更新されない

#### 原因

- Socket.IOイベントが受信されていない
- Chart.jsのデータ更新ロジックが正しくない
- カード全体が再レンダリングされている（グラフだけでなくカード全体が点滅）

#### 解決方法

1. **Socket.IOイベント受信を確認**

```javascript
// pages/monitoring/[id].vue
socket.on('equipment_data_update', (update) => {
  console.log('📊 データ更新:', update)
})
```

2. **Chart.jsのデータ更新を確認**

```javascript
// グラフのみ更新（カード全体は再レンダリングしない）
chart.data.labels.push(new Date(update.timestamp))
chart.data.datasets[0].data.push(update.data.temperature)
chart.update('none')  // アニメーションなしで更新
```

3. **Playwrightテストで確認**

```bash
python scripts/test_monitoring_chart.py
```

### ポート競合

#### 症状

```
Error: listen EADDRINUSE: address already in use :::3000
```

#### 解決方法

```bash
# ポート3000を使用しているプロセスを確認
lsof -i :3000

# プロセスを停止
kill -9 <PID>

# または、別のポートを使用
PORT=3001 npm run dev
```

### キャッシュクリア

#### Nuxtキャッシュクリア

```bash
cd plc-dashboard
rm -rf .nuxt node_modules/.cache
npm run dev
```

#### Pythonキャッシュクリア

```bash
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Playwrightによる動作確認

**重要:** フロントエンド、バックエンド、または統合的な機能を変更した場合は、**作業完了前に必ずPlaywrightで動作確認を実施すること。**

### テストの実行

```bash
# モニタリング画面のグラフ更新テスト（推奨）
python scripts/test_monitoring_chart.py

# クイック動作確認
python scripts/quick_verify.py

# E2Eデプロイメントテスト
python scripts/test_e2e_deployment.py
```

### 確認ポイント

- ✅ ログイン画面が正常に表示されるか
- ✅ モニタリング画面でグラフが表示されるか
- ✅ リアルタイムデータ更新が正常に動作するか
- ✅ カード全体ではなく、グラフ（canvas）のみが更新されるか
- ✅ JavaScriptエラーが発生していないか

### テストスクリプトの作成

新機能を追加した場合は、`scripts/`ディレクトリに対応するPlaywrightテストスクリプトを作成することを推奨します。

## デバッグツール

### データベース統計表示

```bash
cd plc-dashboard/backend
python log_manager.py stats
```

**出力例:**
```
データベース統計:
- 総ログ数: 12,345件
- 設備数: 3台
- 最古のログ: 2025-01-01 00:00:00
- 最新のログ: 2025-01-15 10:30:00
- 日次集計: 45件
- 月次集計: 2件
```

### テーブル確認

```bash
cd plc-dashboard/backend
python check_tables.py
```

**出力例:**
```
テーブル一覧:
- equipment: 3レコード
- plc_data_config: 12レコード
- logs: 12,345レコード
- daily_log_summaries: 45レコード
- monthly_log_summaries: 2レコード
```

### データベースバックアップ

```bash
# PostgreSQLバックアップ
docker compose exec db pg_dump -U plc_user plc_monitor > backup_$(date +%Y%m%d).sql

# データベースリストア
docker compose exec -T db psql -U plc_user plc_monitor < backup_20250115.sql
```

## パフォーマンス測定

### クエリ実行時間の測定

```python
import time
from backend.db import db
from backend.db.models import Log

start_time = time.time()
logs = Log.query.filter_by(equipment_id='DEMO_001').limit(1000).all()
elapsed_time = time.time() - start_time

print(f'クエリ実行時間: {elapsed_time:.3f}秒')
```

### WebSocket遅延の測定

```javascript
// フロントエンド
const sendTime = Date.now()
socket.emit('get_realtime_status', { equipment_id: 'DEMO_001' })

socket.on('realtime_status_response', (data) => {
  const receiveTime = Date.now()
  console.log(`WebSocket遅延: ${receiveTime - sendTime}ms`)
})
```

## 関連ドキュメント

- `_docs/architecture/backend.md` - バックエンドアーキテクチャ
- `_docs/architecture/frontend.md` - フロントエンドアーキテクチャ
- `_docs/architecture/realtime-communication.md` - リアルタイム通信
- `_docs/plc-knowledge/troubleshooting.md` - PLCトラブルシューティング
- `_docs/commands/development.md` - 開発コマンド集

---

**最終更新:** 2025-10-30
