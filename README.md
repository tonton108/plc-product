# PLC監視システム（統合版）

PLCからのデータ収集・監視・分析を行う統合システムです。中央ダッシュボードとRaspberry Piエージェントの両方を含みます。

## 🚀 クイックスタート

### 1. 環境設定

```bash
# 環境変数ファイルをコピー
cp .env.example .env

# 必要に応じて.envを編集
# - SECRET_KEY（本番環境では必ず変更）
# - POSTGRES_PASSWORD
# - ADMIN_PASSWORD_HASH
```

### 2. システム起動

#### 方法A: インタラクティブスクリプト（推奨）

```bash
bash start.sh
```

起動モードを選択できます：
1. **中央サーバーのみ** - DB + API + フロントエンド
2. **全機能** - 中央サーバー + Raspberry Piエージェント
3. **エージェントのみ** - 開発・テスト用
4. **DB + API のみ** - バックエンド開発用

#### 方法B: 直接コマンド

```bash
# 中央サーバーのみ起動
docker compose up -d db backend frontend

# 全機能起動（エージェント含む）
docker compose --profile full up -d

# エージェントのみ起動
docker compose --profile agent up -d
```

### 3. アクセス

| サービス | URL | 説明 |
|---------|-----|------|
| フロントエンド | http://localhost:3000 | Nuxt.jsダッシュボード |
| バックエンドAPI | http://localhost:5000 | Flask REST API |
| エージェントUI | http://localhost:5001 | Raspberry Pi設定画面 |
| PostgreSQL | localhost:5432 | データベース |

### 4. 停止

```bash
# インタラクティブ停止
bash stop.sh

# または直接コマンド
docker compose down           # コンテナ削除（データ保持）
docker compose down -v        # データも削除
```

## 📋 システム構成

```
plc-product/
├── docker-compose.yml        # 統合Docker Compose設定
├── start.sh                  # 起動スクリプト
├── stop.sh                   # 停止スクリプト
├── .env.example              # 環境変数テンプレート
│
├── plc-dashboard/            # メインプロジェクト
│   ├── backend/              # Flask API（共通）
│   ├── raspi_agent/          # Raspberry Piエージェント
│   ├── pages/                # Nuxt.jsページ
│   ├── components/           # Vueコンポーネント
│   └── plugins/              # Nuxt.jsプラグイン
│
└── raspi_plc_ui/             # 旧プロジェクト（参考用）
```

## 🔧 開発コマンド

### Docker Composeコマンド

```bash
# コンテナ起動
docker compose up -d                    # バックグラウンド起動
docker compose up                       # フォアグラウンド起動

# ログ確認
docker compose logs -f                  # 全てのログ
docker compose logs -f backend          # バックエンドのみ
docker compose logs -f frontend         # フロントエンドのみ

# コンテナ状態確認
docker compose ps                       # 実行中のコンテナ
docker compose ps -a                    # 全てのコンテナ

# コンテナ再起動
docker compose restart backend          # 特定サービス
docker compose restart                  # 全サービス

# コンテナ内でコマンド実行
docker compose exec backend bash        # バックエンドコンテナに入る
docker compose exec db psql -U plc_user -d plc_monitor  # PostgreSQL接続
```

### データベース管理

```bash
# マイグレーション実行
docker compose exec backend flask --app manage.py db upgrade

# マイグレーション作成
docker compose exec backend flask --app manage.py db migrate -m "説明"

# データベース統計確認
docker compose exec backend python log_manager.py stats

# 古いデータクリーンアップ
docker compose exec backend python log_manager.py cleanup --days 90
```

### デモデータ送信

```bash
# デモデータを連続送信
docker compose exec backend python demo_data_sender.py --mode continuous --interval 2.0

# 単発送信
docker compose exec backend python demo_data_sender.py --mode single
```

### ローカル開発（Docker不使用）

#### バックエンド

```bash
cd plc-dashboard/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 環境変数設定
export DATABASE_URL="postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor"

# 起動
flask --app manage.py run --host=0.0.0.0 --port=5000
```

#### フロントエンド

```bash
cd plc-dashboard
npm install
npm run dev
```

#### Raspberry Piエージェント

```bash
cd plc-dashboard/raspi_agent
pip install -r requirements_agent.txt

# ダミーモード
export USE_DUMMY_PLC=true
python agent_app.py

# 実機PLC接続
export USE_DUMMY_PLC=false
export PLC_IP=192.168.0.10
python agent_app.py
```

## 🖥️ Raspberry Piへのデプロイ

### 準備

1. `plc-dashboard/raspi_agent/ip_list.csv`にラズパイのIPを記載:

```csv
ip_address
192.168.0.101
192.168.0.102
```

2. SSH接続確認（ユーザー: `pi`）

### デプロイ実行

```bash
cd plc-dashboard/raspi_agent
bash scp_bulk_push.sh
```

### ラズパイ側での確認

```bash
# SSHでラズパイに接続
ssh pi@192.168.0.101

# サービス状態確認
sudo systemctl status plc_ui.service

# ログ確認
sudo journalctl -u plc_ui.service -f

# サービス再起動
sudo systemctl restart plc_ui.service
```

## 🛠️ トラブルシューティング

### コンテナが起動しない

```bash
# ログを確認
docker compose logs backend

# コンテナを再ビルド
docker compose build --no-cache backend
docker compose up -d backend
```

### データベース接続エラー

```bash
# PostgreSQL接続確認
docker compose exec db psql -U plc_user -d plc_monitor

# データベースヘルスチェック
docker compose ps db
```

### ポート競合

.envファイルでポート番号を変更:

```env
POSTGRES_PORT=5433
# 起動後: localhost:5433でアクセス
```

### ボリュームのクリーンアップ

```bash
# 警告: 全データが削除されます
docker compose down -v
docker volume prune
```

## 📚 詳細ドキュメント

- [plc-dashboard/README_INTEGRATED.md](plc-dashboard/README_INTEGRATED.md) - 詳細な使用方法
- [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) - 統合内容のサマリー
- [CLAUDE.md](CLAUDE.md) - 開発者向け技術仕様

## 🔐 セキュリティ

### デフォルト認証情報

- ユーザー名: `admin`
- パスワード: `admin123`

**⚠️ 本番環境では必ず変更してください！**

### パスワード変更方法

1. 新しいパスワードのハッシュを生成:

```bash
python -c "import hashlib; print(hashlib.sha256('新しいパスワード'.encode()).hexdigest())"
```

2. `.env`ファイルの`ADMIN_PASSWORD_HASH`を更新

3. コンテナ再起動:

```bash
docker compose restart raspi-agent
```

## 📊 システム要件

- Docker Desktop（最新版）
- Docker Compose v2.0+
- 推奨メモリ: 4GB以上
- 推奨ディスク: 10GB以上（データベース用）

## 🤝 サポート

問題が発生した場合は、以下を確認してください：

1. Dockerが正常に動作しているか
2. `.env`ファイルが正しく設定されているか
3. ポートが他のアプリケーションと競合していないか

それでも解決しない場合は、開発者にご連絡ください。

---

## 📝 ライセンス

このプロジェクトは内部使用を目的としています。
