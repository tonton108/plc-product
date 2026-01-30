# 環境変数設定ガイド

**作成日:** 2025-10-24

## 中央サーバー（plc-dashboard）

`plc-dashboard/.env`

```bash
# データベース接続
DATABASE_URL=postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor

# Flask設定
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Socket.IO設定
CORS_ALLOWED_ORIGINS=*
```

## Raspberry Piエージェント（raspi_agent）

`plc-dashboard/raspi_agent/.env`

```bash
# PLC接続設定
USE_DUMMY_PLC=false               # true=ダミーモード、false=実PLC接続
PLC_IP=192.168.0.10               # PLCのIPアドレス
PLC_PORT=5000                      # PLCポート（三菱:5000, キーエンス:502, オムロン:9600）
PLC_MANUFACTURER=Mitsubishi        # メーカー名（Mitsubishi, KEYENCE, Omron）

# データ収集設定
LOG_INTERVAL_MS=5000               # データ収集間隔（ミリ秒）

# エラー処理設定
MAX_RETRY_ATTEMPTS=3               # 最大リトライ回数
CONNECTION_TIMEOUT=5               # 接続タイムアウト（秒）
READ_TIMEOUT=3                     # 読み取りタイムアウト（秒）

# 中央サーバー設定
CENTRAL_SERVER_IP=192.168.1.10     # 中央サーバーのIPアドレス
CENTRAL_SERVER_PORT=5000           # 中央サーバーのポート

# 認証設定（WebUI）
ADMIN_PASSWORD=admin               # WebUI管理者パスワード

# PLCセキュリティ設定（2025-01追加）
# IPホワイトリスト: 許可するPLC IPアドレス（カンマ区切り）
ALLOWED_PLC_IPS=192.168.0.10,192.168.0.20,192.168.0.30

# 読み取り専用モード: trueの場合、PLCへの書き込みを禁止
READ_ONLY_MODE=true

# ログ設定
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**セキュリティ設定の重要性:**
- `ALLOWED_PLC_IPS`: 空の場合はすべてのIPを許可（推奨しません）
- `READ_ONLY_MODE`: 本番環境では必ずtrueに設定（データ改ざん防止）

## 初回セットアップ手順

**重要:** プロジェクトを初めて起動する前に、必ず.envファイルを作成してください。

```bash
# プロジェクトルートで.envファイルを作成
cd plc-dashboard
cp .env.example .env

# バックエンドディレクトリにもコピー
cp .env backend/.env
```

### PostgreSQL接続確認

**推奨:** 本番環境・開発環境ともにPostgreSQLの使用を強く推奨します。

```bash
# PostgreSQL接続テスト
psql -U plc_user -h localhost -d plc_monitor -c "SELECT version();"

# マイグレーション実行
cd backend
flask --app manage.py db upgrade
```

### SQLiteフォールバック（非推奨）

DATABASE_URL未設定時はSQLiteにフォールバックしますが、**本番環境・開発環境ともにPostgreSQLの使用を強く推奨します**。

```python
# backend/app.py:26-28
database_url = f'sqlite:///{db_path}'  # フォールバック用
```

## 環境別設定例

### 開発環境（ローカル）

**中央サーバー:**
```bash
DATABASE_URL=sqlite:///plc_monitor.db  # SQLiteを使用
FLASK_ENV=development
SECRET_KEY=dev-secret-key
```

**Raspberry Pi:**
```bash
USE_DUMMY_PLC=true                 # ダミーモードで開発
CENTRAL_SERVER_IP=localhost
LOG_LEVEL=DEBUG
```

### 本番環境（工場内LAN）

**中央サーバー:**
```bash
DATABASE_URL=postgresql+psycopg2://plc_user:strong_password@192.168.1.10:5432/plc_monitor
FLASK_ENV=production
SECRET_KEY=production-strong-secret-key-change-me
```

**Raspberry Pi:**
```bash
USE_DUMMY_PLC=false                # 実PLC接続
PLC_IP=192.168.0.10
PLC_MANUFACTURER=Mitsubishi
CENTRAL_SERVER_IP=192.168.1.10
LOG_LEVEL=INFO
```

## セキュリティ注意事項

### SECRET_KEY

**重要:** 本番環境では必ず強力なランダム文字列を使用してください。

```bash
# Pythonで生成
python -c "import secrets; print(secrets.token_hex(32))"
```

### データベースパスワード

**重要:** デフォルトパスワード（`plc_pass`）は必ず変更してください。

```bash
# PostgreSQLパスワード変更
sudo -u postgres psql
ALTER USER plc_user WITH PASSWORD 'new_strong_password';
```

### 管理者パスワード

**重要:** デフォルトパスワード（`admin`）は必ず変更してください。

## トラブルシューティング

### 環境変数が反映されない

```bash
# 環境変数の確認
printenv | grep PLC

# .envファイルの確認
cat .env

# サービス再起動
sudo systemctl restart plc_ui.service
```

### データベース接続エラー

```bash
# PostgreSQL接続確認
psql postgresql://plc_user:plc_pass@localhost:5432/plc_monitor

# データベース存在確認
sudo -u postgres psql -l
```

詳細は `_docs/plc-knowledge/troubleshooting.md` を参照。

## 関連ドキュメント

- `_docs/deployment/raspi-deployment.md` - ラズパイデプロイ
- `_docs/architecture/backend.md` - バックエンドアーキテクチャ
- `_docs/architecture/raspi-agent.md` - Raspberry Piエージェント

---

**最終更新:** 2025-10-30
