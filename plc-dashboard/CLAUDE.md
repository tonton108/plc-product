# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

PLCから取得したデータをリアルタイムで監視・分析するWebアプリケーションです。Raspberry Pi経由でPLCからデータを収集し、Flask APIで保存・配信、Nuxt.js UIでリアルタイム表示を行います。

### アーキテクチャ構成

- **フロントエンド**: Nuxt.js 3 + Vuetify 3 + Chart.js + Socket.IO Client
- **バックエンド**: Flask + Flask-SocketIO + SQLAlchemy
- **データベース**: PostgreSQL（本番環境）/ SQLite（開発環境）
- **リアルタイム通信**: Socket.IO（threading mode）
- **データ収集**: Raspberry Pi + Python（PLCとModbus通信）

### データフロー

```
[PLC] ─Modbus─> [Raspberry Pi] ─HTTP POST─> [Flask API] ─WebSocket─> [Nuxt UI]
                                                    ↓
                                            [PostgreSQL/SQLite]
```

## 開発コマンド

### フロントエンド（Nuxt.js）

```bash
# 開発サーバー起動（ポート3000）
npm run dev

# プロダクションビルド
npm run build

# プレビュー
npm run preview
```

### バックエンド（Flask）

```bash
# Flaskアプリケーション起動
cd backend
flask --app manage.py run --host=0.0.0.0 --port=5000

# または仮想環境で
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app manage.py run
```

### データベース管理

```bash
# マイグレーション実行
cd backend
flask --app manage.py db upgrade

# 初回のみ（マイグレーション初期化）
flask --app manage.py db init

# 新しいマイグレーション作成
flask --app manage.py db migrate -m "マイグレーション名"

# テーブル確認
python backend/check_tables.py

# データベース初期化（開発用）
python init_db.py
```

### データ管理ツール

```bash
# データベース統計表示
python backend/log_manager.py stats

# 古いデータのクリーンアップ（90日以上）
python backend/log_manager.py cleanup --days 90

# 日次集計を手動作成
python backend/log_manager.py daily 2025-01-15

# 月次集計を手動作成
python backend/log_manager.py monthly 2025 1
```

### デモツール

```bash
# PLCデータ送信シミュレーション（2秒間隔で連続送信）
python backend/demo_data_sender.py --mode continuous --interval 2.0

# 単発データ送信テスト
python backend/demo_data_sender.py --mode single

# 設備登録のみ
python backend/demo_data_sender.py --mode register --equipment-id DEMO_001
```

### Docker環境

```bash
# Docker Composeで全体を起動
docker-compose up -d

# ログ確認
docker-compose logs -f backend
docker-compose logs -f frontend

# 停止
docker-compose down
```

## コードアーキテクチャ

### バックエンド構造

#### `backend/app.py`
Flaskアプリケーションのファクトリー関数を定義。CORS設定、SQLAlchemy初期化、Socket.IO初期化（threading mode）、ルート登録を行います。

**重要**: Socket.IOは`async_mode='threading'`で初期化されており、greenletエラーを回避しています。

#### `backend/api/routes.py`
全APIエンドポイントとWebSocketイベントハンドラーを定義：

**REST API**:
- `POST /api/register` - 設備登録（Raspberry Piからの初期登録）
- `GET /api/equipment` - 全設備一覧取得
- `GET /api/equipment/<equipment_id>` - 設備基本情報取得
- `PUT /api/equipment/<equipment_id>` - 設備基本情報保存
- `GET /api/equipment/search?cpu_serial_number=XXX` - CPU番号で設備検索
- `PUT /api/equipment/<equipment_id>/plc_configs` - PLCデータ設定保存
- `GET /api/equipment/<equipment_id>/plc_configs` - PLCデータ設定取得
- `POST /api/logs` - PLCログデータ保存 + WebSocket配信
- `GET /api/logs/<equipment_id>/latest` - 最新ログ取得
- `GET /api/logs/<equipment_id>/history` - 履歴データ取得
- `GET /api/logs/<equipment_id>/history_optimized?period=24h` - 最適化履歴取得
- `POST /api/admin/cleanup` - 手動クリーンアップ実行
- `GET /api/admin/stats` - データベース統計取得
- `POST /api/admin/create_summary` - 集計データ作成

**Socket.IO イベント**:
- `connect` - WebSocket接続確立
- `disconnect` - WebSocket接続切断
- `join_monitoring` - モニタリングルーム参加
- `leave_monitoring` - モニタリングルーム退出
- `get_realtime_status` - リアルタイム状態取得要求
- `plc_data_update` - PLCデータ更新通知（サーバー→クライアント）
- `equipment_data_update` - 設備別データ更新通知（サーバー→クライアント）

**自動スケジューラー**:
- 24時間間隔で自動クリーンアップ実行
- 前日の日次集計自動作成
- 月初に前月の月次集計自動作成

#### `backend/db/models.py`
SQLAlchemyモデル定義：

- **Equipment**: 設備情報（equipment_id, manufacturer, series, ip, plc_ip, mac_address, cpu_serial_number, etc.）
- **PLCDataConfig**: PLCデータ項目設定（data_type, address, scale_factor, plc_data_type）
- **Log**: 詳細ログデータ（90日間保存）
- **DailyLogSummary**: 日次集計データ（365日間保存）
- **MonthlyLogSummary**: 月次集計データ（永続保存）

**重要な識別子の優先順位**:
1. `cpu_serial_number`（Raspberry PiのCPUシリアル番号、不変識別子）
2. `mac_address`（MACアドレス、準不変）
3. `equipment_id`（ユーザー定義ID、可変）

設備検索・更新時は必ずこの優先順位で検索してください。

#### `backend/log_manager.py`
データ保存期間管理とクリーンアップのCLIツール。バックグラウンドで自動実行されるほか、手動実行も可能です。

### フロントエンド構造

#### `pages/index.vue`
トップページ - 設備一覧表示

#### `pages/equipment/[id].vue`
設備設定ページ - 基本設定とPLCデータ項目設定（Raspberry Piからのセットアップフロー）

#### `pages/monitoring/[id].vue`
リアルタイムモニタリングページ - Socket.IOでリアルタイムデータ受信、Chart.jsでグラフ表示

#### `plugins/socket.io.client.ts`
Socket.IO Clientの初期化設定（`/monitoring/[id].vue`内で直接使用）

#### `plugins/vuetify.ts`
Vuetify 3設定（Material Design Icons含む）

## データベース設計の特徴

### 階層化アーカイブシステム

1. **詳細データ（logs）**: 90日間保存、リアルタイム監視・詳細分析用
2. **日次集計（daily_log_summaries）**: 365日間保存、週次・月次トレンド分析用
3. **月次集計（monthly_log_summaries）**: 永続保存、長期比較・年次計画用

### 最適化されたインデックス

- `idx_logs_timestamp` - タイムスタンプ検索の高速化
- `idx_logs_equipment_timestamp` - 設備別期間検索の高速化
- `idx_daily_summary_equipment_date` - 日次集計検索の高速化
- `idx_monthly_summary_equipment_year_month` - 月次集計検索の高速化

### データ保存戦略

`backend/api/routes.py`の`DATA_RETENTION_CONFIG`で設定：
- `raw_data_days`: 90（詳細データ保持期間）
- `daily_data_days`: 365（日次集計保持期間）
- `cleanup_interval_hours`: 24（クリーンアップ実行間隔）

## リアルタイム通信の実装

### Socket.IO接続フロー

1. Nuxt UIが`/monitoring/[id]`ページを開く
2. Socket.IO Clientが`ws://localhost:5000`に接続
3. `join_monitoring`イベントでルーム参加
4. Raspberry Piが`POST /api/logs`でデータ送信
5. Flask APIがDB保存 + `emit('plc_data_update')`で配信
6. Nuxt UIがリアルタイムでグラフ更新

### WebSocketルーム設計

- `monitoring` - 全モニタリングクライアント
- `equipment_{equipment_id}` - 特定設備のモニタリングクライアント

## 環境変数設定

### バックエンド（`backend/.env`）

```env
DATABASE_URL=postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor
SECRET_KEY=your-secret-key
```

SQLiteにフォールバック可能（DATABASE_URL未設定時）：
```python
database_url = 'sqlite:///instance/plc_monitoring.db'
```

## 重要な実装上の注意点

### Socket.IOのGreenletエラー回避

Flask-SocketIOは`async_mode='threading'`で初期化する必要があります：

```python
socketio.init_app(
    app,
    cors_allowed_origins=["http://localhost:3000"],
    async_mode='threading',
    logger=False,
    engineio_logger=False
)
```

### 設備の識別と更新

設備の更新時は必ず`cpu_serial_number`で既存設備を検索し、見つかった場合は`equipment_id`を更新します。これにより、Raspberry Piの再起動やIP変更があっても設備情報を正しく維持できます。

```python
# routes.py:388-432 参照
equipment = Equipment.query.filter_by(cpu_serial_number=cpu_serial_number).first()
if equipment:
    equipment.equipment_id = equipment_id  # 設備IDを新しい値に更新
```

### PLCデータ設定の保存

PLCデータ設定は`PUT /api/equipment/<equipment_id>/plc_configs`で一括保存されます。既存設定を削除してから新しい設定を挿入するため、トランザクション内で実行してください。

### データ最適化クエリ

短期間（1h, 6h, 24h）は詳細データ、長期間（7d, 30d）は集計データを自動的に選択します：

```python
# routes.py:979-1052 参照
if period in ['1h', '6h', '24h']:
    logs = Log.query.filter(...).all()  # 詳細データ
elif period in ['7d', '30d']:
    summaries = DailyLogSummary.query.filter(...).all()  # 集計データ
```

## テストとデバッグ

### デモデータ送信の実行順序

1. バックエンド起動: `flask --app manage.py run`
2. フロントエンド起動: `npm run dev`
3. デモ送信開始: `python backend/demo_data_sender.py --mode continuous`
4. ブラウザで確認: `http://localhost:3000/monitoring/DEMO_001`

### ログの確認

- Flask側: ターミナル出力に詳細なデバッグログ（`📥 PLCデータ受信`, `📡 WebSocket送信完了`等）
- Nuxt側: ブラウザの開発者コンソールでSocket.IOイベント確認

### トラブルシューティング

#### データベース接続エラー
```bash
# PostgreSQL接続確認
python test_db_connection.py
```

#### Socket.IO接続エラー
- CORSオリジン設定を確認（`backend/app.py:18, 47`）
- ポート5000が開いているか確認

#### データが表示されない
1. `GET /api/logs/DEMO_001/latest` でデータ存在確認
2. Socket.IOイベント受信確認（ブラウザコンソール）
3. Flaskログでデータ受信・配信を確認
