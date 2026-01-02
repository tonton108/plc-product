# PLC Monitoring System - Backend

Flask + Flask-SocketIO + SQLAlchemyを使用したPLC監視システムのバックエンドAPI。

## 開発環境での起動

### 開発サーバー（Werkzeug）

```bash
# 仮想環境のセットアップ
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 開発サーバー起動
python manage_simple.py
```

### Dockerでの起動

```bash
# プロジェクトルートから
docker compose up backend
```

## 本番環境での起動

本番環境では**Gunicorn + gevent-websocket**を使用してください。

### Gunicornでの起動方法

```bash
# 基本的な起動
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --bind 0.0.0.0:5000 \
         wsgi:app

# ワーカー数を指定（推奨: CPUコア数 × 2 + 1）
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --workers 4 \
         --bind 0.0.0.0:5000 \
         wsgi:app

# タイムアウトとログ設定を追加
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --workers 4 \
         --bind 0.0.0.0:5000 \
         --timeout 60 \
         --access-logfile - \
         --error-logfile - \
         wsgi:app
```

### Docker Composeで本番環境を起動

`docker-compose.yml`の`backend`サービスの`command`を変更:

```yaml
# 開発環境
command: python manage_simple.py

# 本番環境（推奨）
command: gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker --workers 4 --bind 0.0.0.0:5000 --timeout 60 wsgi:app
```

## 環境変数

`.env`ファイルで設定:

```bash
# データベース
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/dbname

# Flask
SECRET_KEY=your-random-secret-key
FLASK_ENV=production  # 本番環境では必ずproductionに

# CORS
CORS_ORIGINS=https://your-domain.com,https://dashboard.your-domain.com

# ログレベル
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## ディレクトリ構成

```
backend/
├── app.py                  # Flaskアプリケーションファクトリー
├── wsgi.py                 # 本番環境用WSGIエントリーポイント
├── manage_simple.py        # 開発サーバー起動スクリプト
├── docker-entrypoint.sh    # Dockerエントリーポイント
├── logger.py               # ロギング設定
├── error_handlers.py       # 統一されたエラーハンドリング
├── requirements.txt        # Python依存関係
├── api/
│   └── routes.py           # APIエンドポイント定義
├── db/
│   ├── __init__.py         # SQLAlchemy初期化
│   └── models.py           # データベースモデル
└── instance/
    └── plc_monitoring.db   # SQLiteデータベース（開発環境）
```

## API エンドポイント

### 設備管理

- `POST /api/register` - 設備登録
- `GET /api/equipment` - 全設備一覧取得
- `GET /api/equipment/<equipment_id>` - 設備詳細取得
- `PUT /api/equipment/<equipment_id>` - 設備情報更新
- `GET /api/equipment/search?cpu_serial_number=XXX` - 設備検索

### PLCデータ

- `POST /api/logs` - PLCログデータ保存
- `GET /api/logs/<equipment_id>/latest` - 最新データ取得
- `GET /api/logs/<equipment_id>/history` - 履歴データ取得
- `GET /api/logs/<equipment_id>/history_optimized?period=24h` - 最適化履歴取得

### 管理機能

- `GET /api/admin/stats` - データベース統計
- `POST /api/admin/cleanup` - 古いデータクリーンアップ
- `POST /api/admin/create_summary` - 集計データ作成

## WebSocket (Socket.IO)

### イベント

**クライアント → サーバー:**
- `connect` - 接続確立
- `join_monitoring` - モニタリングルーム参加
- `leave_monitoring` - モニタリングルーム退出
- `get_realtime_status` - リアルタイム状態取得

**サーバー → クライアント:**
- `plc_data_update` - PLCデータ更新通知
- `equipment_data_update` - 設備別データ更新通知

## データベースマイグレーション

起動時に自動的にテーブルが作成されます（`docker-entrypoint.sh`）。

手動でテーブルを作成する場合:

```python
python -c "from app import create_app, db; app, _ = create_app(); app.app_context().push(); db.create_all()"
```

## トラブルシューティング

### データベース接続エラー

```bash
# PostgreSQL接続確認
psql -h localhost -p 5432 -U plc_user -d plc_monitor

# Docker内のPostgreSQL確認
docker compose exec db psql -U plc_user -d plc_monitor
```

### ポート競合

デフォルトポート5000が使用中の場合:

```bash
# 別のポートで起動
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

### Socket.IO接続エラー

- CORS設定を確認（`app.py`の`cors_allowed_origins`）
- ファイアウォール設定を確認
- ブラウザの開発者コンソールでエラーメッセージを確認

## パフォーマンスチューニング

### データベース接続プール

`app.py`で設定:

```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,         # 通常の接続プールサイズ（200台規模対応）
    'max_overflow': 50,      # 最大追加接続数（合計70接続まで対応）
    'pool_timeout': 30,      # 接続タイムアウト
    'pool_recycle': 300,     # 接続リサイクル時間
}
```

### Gunicornワーカー数

```bash
# CPUコア数を確認
nproc  # Linux
sysctl -n hw.ncpu  # macOS

# 推奨ワーカー数: (CPUコア数 × 2) + 1
gunicorn --workers 9 wsgi:app  # 4コアの場合
```

## ログ設定

環境変数`LOG_LEVEL`でログレベルを制御:

```bash
# 開発環境
export LOG_LEVEL=DEBUG

# 本番環境
export LOG_LEVEL=INFO
```

ログはSTDOUTに出力されます。本番環境ではログ収集ツール（例: Fluentd, Logstash）と連携してください。
