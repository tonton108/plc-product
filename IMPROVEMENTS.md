# システム改善提案書

本ドキュメントは、PLCモニタリングシステムの実装において改善すべき点をまとめたものです。

---

## 🔴 Critical (緊急対応が必要)

### 1. `.gitignore` ファイルの不足

**問題点:**
- `.gitignore` ファイルが存在しないため、機密情報を含む `.env` ファイルや、node_modules、ビルド成果物がGitにコミットされる危険性があります。

**影響度:** 🔴 **Critical**

**推奨対応:**
```gitignore
# 環境変数ファイル
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
instance/
*.db
*.sqlite

# Node.js
node_modules/
.nuxt/
.output/
.cache/
dist/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
.dockerignore

# Logs
*.log
logs/
```

---

### 2. デフォルトの機密情報がハードコードされている

**問題点:**
- `.env` ファイルに以下のような脆弱な設定が含まれています:
  - `POSTGRES_PASSWORD=plc_pass` (弱いパスワード)
  - `SECRET_KEY=your-secure-secret-key-change-in-production` (デフォルト値)
  - `ADMIN_PASSWORD_HASH=e2c6ed4d94bc3d1b605cb5fe7e92e48546b26e0f1e30f97e8151af9f9abb0844` (admin123のハッシュ)

**影響度:** 🔴 **Critical**

**推奨対応:**
1. `.env.example` を作成し、実際の `.env` は `.gitignore` に追加
2. 本番環境では強固なパスワード・シークレットキーを使用
3. 初回起動時にランダムな値を生成するスクリプトを提供

```bash
# .env.example に以下を記載
POSTGRES_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD
SECRET_KEY=CHANGE_ME_TO_RANDOM_SECRET_KEY
ADMIN_PASSWORD_HASH=CHANGE_ME_AFTER_RUNNING_HASH_SCRIPT
```

---

### 3. 本番環境で開発サーバーを使用している

**問題点:**
- `manage_simple.py` で `allow_unsafe_werkzeug=True` を使用
- Werkzeugの開発サーバーは本番環境での使用が推奨されていません
- パフォーマンス、セキュリティ、安定性に問題があります

**影響度:** 🔴 **Critical**

**推奨対応:**
本番環境では Gunicorn + gevent-websocket を使用してください。

**修正案:**

`plc-dashboard/backend/requirements.txt` に追加:
```txt
gunicorn==21.2.0
gevent==23.9.1
gevent-websocket==0.10.1
```

`plc-dashboard/backend/wsgi.py` を新規作成:
```python
from app import create_app

app, socketio = create_app()

if __name__ == "__main__":
    socketio.run(app)
```

`docker-compose.yml` の本番環境用コマンド:
```yaml
# 開発環境
command: python manage_simple.py

# 本番環境 (推奨)
command: gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker --bind 0.0.0.0:5000 wsgi:app
```

---

## 🟠 High (早期対応が推奨)

### 4. Docker Composeの `version` フィールドが非推奨

**問題点:**
- `docker-compose.yml` の `version: '3.8'` は現在非推奨です
- 警告メッセージが毎回表示されます

**影響度:** 🟠 **High**

**推奨対応:**
`docker-compose.yml` の1行目を削除してください:
```yaml
# 削除
version: '3.8'

# そのまま services: から開始
services:
  db:
    ...
```

---

### 5. データベースマイグレーションの管理が不完全

**問題点:**
- 現在は `db.create_all()` で直接テーブルを作成していますが、これは本番環境では推奨されません
- Flask-Migrate (Alembic) が設定されていますが、正しく機能していません

**影響度:** 🟠 **High**

**推奨対応:**

1. マイグレーション初期化スクリプトを作成:

`plc-dashboard/backend/init_migrations.py`:
```python
from app import create_app, db
import os

app, socketio = create_app()

with app.app_context():
    # 既存のテーブル構造からマイグレーションを作成
    os.system('flask --app manage.py db init')
    os.system('flask --app manage.py db migrate -m "Initial migration"')
    os.system('flask --app manage.py db upgrade')
```

2. Dockerfile のエントリーポイントで自動マイグレーション:
```dockerfile
# エントリーポイントスクリプトを作成
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
```

`docker-entrypoint.sh`:
```bash
#!/bin/bash
set -e

# マイグレーション実行
python -c "from app import create_app, db; app, _ = create_app(); app.app_context().push(); db.create_all()"

# アプリケーション起動
exec "$@"
```

---

### 6. ヘルスチェックの失敗

**問題点:**
- バックエンドのヘルスチェックが "unhealthy" になっていますが、これはcurlがコンテナにインストールされていないためです

**影響度:** 🟠 **High**

**推奨対応:**

`plc-dashboard/backend/Dockerfile` を修正:
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

または、Pythonスクリプトを使用したヘルスチェック:

`docker-compose.yml`:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5000/api/equipment')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## 🟡 Medium (改善を検討)

### 7. CORS設定が開発環境向けに固定されている

**問題点:**
- `app.py` で CORS のオリジンが `localhost:3000` と `localhost:3001` に固定されています
- 本番環境では実際のドメインを指定する必要があります

**影響度:** 🟡 **Medium**

**推奨対応:**

`plc-dashboard/backend/app.py`:
```python
# 環境変数からCORSオリジンを取得
import os

allowed_origins = os.getenv(
    'CORS_ORIGINS',
    'http://localhost:3000,http://localhost:3001'
).split(',')

CORS(app, origins=allowed_origins)

socketio.init_app(
    app,
    cors_allowed_origins=allowed_origins,
    async_mode='threading',
    logger=False,
    engineio_logger=False
)
```

`.env` に追加:
```bash
# 開発環境
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# 本番環境の例
# CORS_ORIGINS=https://plc-monitor.example.com,https://dashboard.example.com
```

---

### 8. ログレベルとログ出力の管理が不十分

**問題点:**
- デバッグログ (`print` 文) がコード全体に散在しています
- 本番環境では適切なログレベル管理が必要です

**影響度:** 🟡 **Medium**

**推奨対応:**

Python標準の `logging` モジュールを使用:

`plc-dashboard/backend/logger.py` (新規作成):
```python
import logging
import os

def setup_logger():
    log_level = os.getenv('LOG_LEVEL', 'INFO')

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    return logging.getLogger('plc_monitor')

logger = setup_logger()
```

使用例:
```python
# 変更前
print(f"📥 PLCデータ受信: 設備ID={equipment_id}")

# 変更後
from logger import logger
logger.info(f"PLCデータ受信: 設備ID={equipment_id}")
```

`.env` に追加:
```bash
# 開発環境
LOG_LEVEL=DEBUG

# 本番環境
LOG_LEVEL=INFO
```

---

### 9. データベース接続プールの設定が不足

**問題点:**
- 高負荷時の接続プール管理が最適化されていません
- `pool_size` と `max_overflow` が明示的に設定されていません

**影響度:** 🟡 **Medium**

**推奨対応:**

`plc-dashboard/backend/app.py`:
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_size': 10,           # 通常の接続プールサイズ
    'max_overflow': 20,        # 最大追加接続数
    'pool_timeout': 30,        # 接続タイムアウト(秒)
    'echo': False,
    'connect_args': {
        'check_same_thread': False,
    } if 'sqlite' in database_url else {}
}
```

---

### 10. フロントエンドの環境変数が動的に読み込まれていない

**問題点:**
- `NUXT_PUBLIC_API_BASE` が `http://backend:5000` になっており、ブラウザからはアクセスできません
- Dockerネットワーク内部のホスト名がブラウザに公開されています

**影響度:** 🟡 **Medium**

**推奨対応:**

`nuxt.config.ts`:
```typescript
export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:5000'
    }
  }
})
```

`docker-compose.yml`:
```yaml
frontend:
  environment:
    # ブラウザからアクセス可能なURL
    NUXT_PUBLIC_API_BASE: http://localhost:5000
```

使用例 (コンポーネント内):
```typescript
const config = useRuntimeConfig()
const apiUrl = config.public.apiBase
```

---

## 🟢 Low (任意の改善)

### 11. SQLインジェクション対策の強化

**問題点:**
- `api/routes.py` の一部で `text()` を使った生SQLが使用されています
- 現在は適切にパラメータ化されていますが、SQLAlchemy ORM の使用が望ましいです

**影響度:** 🟢 **Low** (現状は問題なし)

**推奨対応:**

```python
# 変更前 (routes.py:1018-1023)
summaries = db.session.query(DailyLogSummary)\
    .filter_by(equipment_id=equipment.id)\
    .filter(text("date >= :start_date"))\
    .params(start_date=start_date)\
    .order_by(text("date DESC"))\
    .all()

# 変更後
summaries = db.session.query(DailyLogSummary)\
    .filter_by(equipment_id=equipment.id)\
    .filter(DailyLogSummary.date >= start_date)\
    .order_by(DailyLogSummary.date.desc())\
    .all()
```

---

### 12. エラーハンドリングの標準化

**問題点:**
- API全体で一貫したエラーレスポンス形式が使用されていません
- HTTPステータスコードが適切でない箇所があります

**影響度:** 🟢 **Low**

**推奨対応:**

エラーハンドラーを統一:

`plc-dashboard/backend/error_handlers.py` (新規作成):
```python
from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': str(error)
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': str(error)
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
```

`app.py` で登録:
```python
from error_handlers import register_error_handlers
register_error_handlers(app)
```

---

### 13. テストコードの追加

**問題点:**
- 単体テストや統合テストが存在しません
- CI/CDパイプラインで自動テストができません

**影響度:** 🟢 **Low**

**推奨対応:**

テストフレームワークの導入:

`plc-dashboard/backend/requirements-dev.txt`:
```txt
pytest==7.4.3
pytest-flask==1.3.0
pytest-cov==4.1.0
```

`plc-dashboard/backend/tests/test_api.py`:
```python
import pytest
from app import create_app, db

@pytest.fixture
def client():
    app, socketio = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_get_equipment(client):
    response = client.get('/api/equipment')
    assert response.status_code == 200
    assert isinstance(response.json, list)
```

---

### 14. Docker イメージサイズの最適化

**問題点:**
- マルチステージビルドを使用していないため、イメージサイズが大きくなっています

**影響度:** 🟢 **Low**

**推奨対応:**

`plc-dashboard/backend/Dockerfile`:
```dockerfile
# ビルドステージ
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 実行ステージ
FROM python:3.11-slim

WORKDIR /app

# ビルドステージからPythonパッケージをコピー
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

EXPOSE 5000
ENV PYTHONPATH=/app
CMD ["python", "manage_simple.py"]
```

---

## ✅ 良好な実装ポイント

以下の点は既にベストプラクティスに従っています:

1. **データベース設計**
   - 階層化アーカイブシステム (90日/365日/永続保存)
   - 適切なインデックス設計
   - 正規化されたテーブル構造

2. **API設計**
   - RESTful API の原則に従っている
   - 適切なHTTPメソッドの使用
   - WebSocketとREST APIの適切な使い分け

3. **Docker構成**
   - ヘルスチェックの実装
   - 環境変数による設定の外部化
   - ネットワーク分離

4. **セキュリティ意識**
   - パスワードのハッシュ化
   - 環境変数による機密情報の管理
   - CORS設定の実装

---

## 優先度別実装推奨順序

### フェーズ1: セキュリティ対応 (即時実施)
1. `.gitignore` の追加
2. `.env.example` の作成と `.env` の除外
3. 本番環境用の強固なパスワード・シークレットキーの生成

### フェーズ2: 本番環境対応 (1週間以内)
4. Gunicorn への移行
5. `version` フィールドの削除
6. ヘルスチェックの修正
7. CORS設定の環境変数化

### フェーズ3: 運用改善 (1ヶ月以内)
8. ログ管理の標準化
9. データベース接続プールの最適化
10. マイグレーション管理の改善

### フェーズ4: 品質向上 (随時)
11. テストコードの追加
12. エラーハンドリングの標準化
13. SQLクエリの最適化
14. Dockerイメージの最適化

---

## まとめ

現在の実装は**基本的に良好**ですが、本番環境へのデプロイ前に以下の対応が必須です:

- 🔴 機密情報の保護 (.gitignore, 環境変数)
- 🔴 本番環境用サーバー (Gunicorn)
- 🟠 ヘルスチェックの修正

その他の改善点は段階的に対応することで、よりロバストで保守性の高いシステムになります。
