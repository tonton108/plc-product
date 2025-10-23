# PLC監視システム統合版

PLCデータ収集・監視・分析システムの統合版です。中央サーバーとRaspberry Piエージェントの両方を含みます。

## 📁 プロジェクト構成

```
plc-dashboard/
├── backend/              # Flask API（中央サーバー・エージェント共通）
│   ├── api/             # APIルート定義
│   ├── db/              # データベースモデル
│   ├── manage.py        # Flask CLI
│   └── Dockerfile       # Dockerイメージ
├── raspi_agent/         # Raspberry Piエージェント
│   ├── agent_app.py     # エージェントアプリケーション
│   ├── plc_agent.py     # PLCデータ収集エージェント
│   ├── db_utils.py      # ローカル設定管理
│   ├── templates/       # WebUI（ラズパイ用）
│   ├── config/          # 設定ファイル
│   ├── scp_bulk_push.sh # ラズパイへの一括デプロイスクリプト
│   └── Dockerfile.agent # Dockerイメージ
├── pages/               # Nuxt.jsページ（中央ダッシュボード）
├── components/          # Vueコンポーネント
├── plugins/             # Nuxt.jsプラグイン
├── docker-compose.yml   # 統合Docker Compose設定
├── nuxt.config.ts       # Nuxt.js設定
└── README_INTEGRATED.md # このファイル
```

## 🚀 クイックスタート

### 前提条件

- Docker & Docker Compose
- Node.js 18+ & npm（フロントエンド開発時）
- Python 3.10+（ローカル開発時）

### 1. 環境設定

```bash
cd plc-dashboard

# 環境変数ファイルをコピー
cp .env.example .env

# 必要に応じて.envを編集
# - DATABASE_URL（PostgreSQL接続情報）
# - SECRET_KEY（セキュリティキー）
```

### 2. 中央サーバーモードで起動

中央ダッシュボード + バックエンドAPI + データベースを起動します。

```bash
# Docker Composeで起動
docker compose up -d db backend

# データベースマイグレーション実行
docker compose exec backend flask --app manage.py db upgrade

# フロントエンド（Nuxt.js）を起動（開発モード）
npm install
npm run dev
```

**アクセス:**
- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:5000

### 3. Raspberry Piエージェントモード（オプション）

Raspberry Pi上で動作するPLCデータ収集エージェントをローカルテストします。

```bash
# エージェントプロファイルで起動
docker compose --profile agent up -d raspi-agent

# または、ローカルPythonで起動
cd raspi_agent
python agent_app.py
```

**アクセス:**
- エージェントWebUI: http://localhost:5001

## 🖥️ 動作モード

### モード1: 中央サーバー（ダッシュボード）

複数のRaspberry Piエージェントからデータを収集し、Webダッシュボードでリアルタイム監視・分析を行います。

**起動コマンド:**
```bash
docker compose up -d db backend
npm run dev  # Nuxt.jsフロントエンド
```

**主な機能:**
- 複数設備のリアルタイムモニタリング
- WebSocketによるリアルタイムデータ配信
- 履歴データのグラフ表示
- 階層化アーカイブ（90日・365日・永続）
- データベース管理・クリーンアップ

### モード2: Raspberry Piエージェント

Raspberry Pi上で動作し、PLCからデータを収集して中央サーバーに送信します。

**起動コマンド:**
```bash
# Dockerで起動
docker compose --profile agent up -d raspi-agent

# または直接起動
cd raspi_agent
python agent_app.py
```

**主な機能:**
- PLC自動接続（三菱、オムロン、キーエンス、シーメンス対応）
- CPUシリアル番号による自動設備識別
- ダミーモード（PLC未接続時の開発用）
- ローカルWebUI（初期設定・モニタリング）
- 認証機能

## 📋 開発コマンド

### バックエンド（Flask）

```bash
cd backend

# ローカル開発サーバー起動
flask --app manage.py run --host=0.0.0.0 --port=5000

# データベースマイグレーション
flask --app manage.py db upgrade      # マイグレーション実行
flask --app manage.py db migrate -m "説明"  # 新しいマイグレーション作成

# データ管理ツール
python log_manager.py stats                  # 統計表示
python log_manager.py cleanup --days 90     # 90日以上古いデータ削除
python log_manager.py daily 2025-01-15      # 日次集計作成

# デモデータ送信
python demo_data_sender.py --mode continuous --interval 2.0
```

### フロントエンド（Nuxt.js）

```bash
# 開発サーバー起動（ホットリロード有効）
npm run dev

# プロダクションビルド
npm run build

# プロダクションプレビュー
npm run preview
```

### Raspberry Piエージェント

```bash
cd raspi_agent

# ローカル開発（ダミーPLCモード）
export USE_DUMMY_PLC=true
python agent_app.py

# 実機PLC接続モード
export USE_DUMMY_PLC=false
export PLC_IP=192.168.0.10
python agent_app.py

# PLCエージェント単体テスト
python plc_agent.py

# CPUシリアル番号確認
python test_cpu_serial.py
```

## 🚀 Raspberry Piへのデプロイ

### 準備

1. `raspi_agent/ip_list.csv`にデプロイ対象のラズパイIPを記載:

```csv
ip_address
192.168.0.101
192.168.0.102
```

2. ラズパイにSSH接続可能であることを確認（ユーザー: `pi`）

### 一括デプロイ

```bash
cd raspi_agent
bash scp_bulk_push.sh
```

このスクリプトは以下を実行します:
- プロジェクトフォルダを`/home/pi/plc-product/`に転送
- `plc_ui.service`を`/etc/systemd/system/`に設置
- systemd経由でDocker Composeを自動起動・永続化

### ラズパイ側の動作確認

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

### 初期設定

ブラウザで`http://<ラズパイIP>:5001`にアクセスし、初期設定を行います:

1. **認証**: デフォルトユーザー名 `admin`、パスワード `admin123`
2. **設備情報**: 設備ID、メーカー、シリーズを設定
3. **PLC接続**: PLC IPアドレス、ポート、データ項目を設定
4. **セキュリティ**: 管理者パスワードを設定

## 🔧 環境変数

| 変数名 | デフォルト | 説明 |
|--------|----------|------|
| `POSTGRES_USER` | `plc_user` | PostgreSQLユーザー名 |
| `POSTGRES_PASSWORD` | `plc_pass` | PostgreSQLパスワード |
| `POSTGRES_DB` | `plc_monitor` | PostgreSQLデータベース名 |
| `DATABASE_URL` | 自動生成 | データベース接続URL |
| `SECRET_KEY` | - | Flask セキュリティキー（必須） |
| `CENTRAL_SERVER_IP` | `localhost` | 中央サーバーIP |
| `CENTRAL_SERVER_PORT` | `5000` | 中央サーバーポート |
| `RASPI_UI_PORT` | `5001` | ラズパイWebUIポート |
| `USE_DUMMY_PLC` | `true` | ダミーPLCモード（開発用） |
| `PLC_IP` | `192.168.1.100` | PLC IPアドレス |
| `PLC_MANUFACTURER` | `Mitsubishi` | PLCメーカー |
| `REQUIRE_AUTH` | `true` | 認証必須モード |

## 🛠️ トラブルシューティング

### データベース接続エラー

```bash
# PostgreSQL接続確認
docker compose exec backend python test_db_connection.py

# マイグレーション実行
docker compose exec backend flask --app manage.py db upgrade
```

### Socket.IO Greenletエラー

Socket.IOは必ず`async_mode='threading'`で初期化してください:
```python
socketio.init_app(app, async_mode='threading')
```

### 設備が見つからない

1. CPUシリアル番号を確認:
```bash
cd raspi_agent
python test_cpu_serial.py
```

2. 中央サーバーで設備検索:
```bash
curl "http://localhost:5000/api/equipment/search?cpu_serial_number=XXX"
```

3. 設備が未登録なら、ラズパイ側のWebUI（http://localhost:5001）で初期設定を実行

### PLC接続エラー

1. ダミーモードで動作確認:
```bash
export USE_DUMMY_PLC=true
python raspi_agent/agent_app.py
```

2. PLC側の設定確認:
   - IPアドレス
   - ポート番号
   - 通信プロトコル（Modbus/FINS/MC Protocol）

## 📊 データベース管理

### データ保存戦略

- **詳細データ（logs）**: 90日間保存、リアルタイム監視用
- **日次集計（daily_log_summaries）**: 365日間保存、トレンド分析用
- **月次集計（monthly_log_summaries）**: 永続保存、長期比較用

### クリーンアップ

```bash
# 自動クリーンアップ（24時間間隔で実行）
# システム起動時に自動開始

# 手動クリーンアップ
cd backend
python log_manager.py cleanup --days 90

# データベース統計確認
python log_manager.py stats
```

## 📚 詳細ドキュメント

- [CLAUDE.md](./CLAUDE.md) - Claude Code向けの詳細技術仕様
- [backend/README.md](./backend/README.md) - バックエンドAPI仕様
- [raspi_agent/README.md](./raspi_agent/README.md) - ラズパイエージェント仕様

## 🤝 サポート

不具合・質問は開発者までご連絡ください。
