# 開発コマンド集

**作成日:** 2025-10-24

## クイックスタート

### 中央サーバー起動

```bash
cd plc-dashboard

# 環境設定
cp .env.example .env

# PostgreSQL + Flask Backend
docker compose up -d db backend

# Nuxt.js Frontend (ポート3000)
npm run dev
```

### Raspberry Piエージェント起動（ローカル開発）

```bash
cd plc-dashboard/raspi_agent

# ダミーPLCモード
export USE_DUMMY_PLC=true
python agent_app.py  # ポート8080
```

## バックエンド（Flask）

### 開発サーバー

```bash
cd plc-dashboard/backend

# Flask開発サーバー起動
flask --app manage.py run --host=0.0.0.0 --port=5000
```

### データベースマイグレーション

```bash
# マイグレーション適用
flask --app manage.py db upgrade

# 新しいマイグレーション作成
flask --app manage.py db migrate -m "説明"

# マイグレーション履歴確認
flask --app manage.py db history
```

### データ管理ツール

```bash
# 統計表示
python log_manager.py stats

# 古いログをクリーンアップ（--days省略時は既定30日。SPEC §5.2）
python log_manager.py cleanup --days 30

# 特定日の日次集計作成
python log_manager.py daily 2025-01-15

# 特定月の月次集計作成
python log_manager.py monthly 2025 1
```

### デモデータ送信（開発用）

```bash
# 継続的にデモデータを送信（2秒間隔）
python demo_data_sender.py --mode continuous --interval 2.0

# 1回だけデモデータを送信
python demo_data_sender.py --mode once
```

## フロントエンド（Nuxt.js）

### 開発サーバー

```bash
cd plc-dashboard

# ホットリロード付き開発サーバー（ポート3000）
npm run dev
```

### プロダクションビルド

```bash
# ビルド
npm run build

# プレビュー
npm run preview
```

### Linting

```bash
# ESLint実行
npm run lint

# ESLint自動修正
npm run lint:fix
```

## Raspberry Piエージェント

### ローカル開発

```bash
cd plc-dashboard/raspi_agent

# ダミーPLCモード（PLCなしで開発）
export USE_DUMMY_PLC=true
python agent_app.py

# 実機PLC接続モード
export USE_DUMMY_PLC=false
export PLC_IP=192.168.0.10
python agent_app.py
```

### ラズパイへのデプロイ

```bash
# ip_list.csvに対象IPアドレスを記載
# 例: 192.168.0.101, 192.168.0.102

# 一括デプロイ実行
bash scp_bulk_push.sh
```

詳細は `_docs/deployment/raspi-deployment.md` を参照。

## Docker Compose

### 基本コマンド

```bash
cd plc-dashboard

# すべてのサービスを起動
docker compose up -d

# 特定のサービスのみ起動
docker compose up -d db backend

# Raspberry Piエージェントモード起動
docker compose --profile agent up -d raspi-agent

# ログ確認
docker compose logs -f backend

# サービス停止
docker compose down

# ボリュームも削除して完全にクリーンアップ
docker compose down -v
```

### データベース接続

```bash
# PostgreSQLコンテナに接続
docker compose exec db psql -U plc_user -d plc_monitor

# データベースバックアップ
docker compose exec db pg_dump -U plc_user plc_monitor > backup.sql

# データベースリストア
docker compose exec -T db psql -U plc_user plc_monitor < backup.sql
```

## テスト

### バックエンドテスト

```bash
cd plc-dashboard/backend

# すべてのテストを実行
pytest

# カバレッジ付きでテスト実行
pytest --cov=. --cov-report=html

# 特定のテストファイルのみ実行
pytest tests/test_plc_drivers.py

# テスト結果の詳細表示
pytest -v
```

### フロントエンドテスト

```bash
cd plc-dashboard

# ビルドテスト
npm run build

# Lintテスト
npm run lint
```

## トラブルシューティング

### データベース接続テスト

```bash
cd plc-dashboard
python scripts/test_db_connection.py
```

### ポート確認

```bash
# ポート3000が使用中か確認
lsof -i :3000

# ポート5000が使用中か確認
lsof -i :5000
```

### キャッシュクリア

```bash
# Nuxtキャッシュクリア
cd plc-dashboard
rm -rf .nuxt node_modules/.cache

# Pythonキャッシュクリア
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## 関連ドキュメント

- `_docs/architecture/backend.md` - バックエンドアーキテクチャ
- `_docs/architecture/frontend.md` - フロントエンドアーキテクチャ
- `_docs/architecture/raspi-agent.md` - Raspberry Piエージェント
- `_docs/deployment/raspi-deployment.md` - ラズパイデプロイ
- `_docs/deployment/environment-variables.md` - 環境変数設定

---

**最終更新:** 2025-10-24
