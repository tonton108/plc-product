# PLC監視システム 統合版

PLCデータ収集・監視・分析システムの統合版です。中央サーバーとRaspberry Piエージェントの両方を含みます。

## 📁 プロジェクト構成

```
plc-dashboard/
├── backend/              # Flask API（中央サーバー）
│   ├── api/             # APIルート定義
│   ├── db/              # データベースモデル
│   ├── test_data/       # テストデータ（整理済み）
│   └── Dockerfile       # Dockerイメージ
├── raspi_agent/         # Raspberry Piエージェント
│   ├── agent_app.py     # エージェントアプリケーション
│   ├── plc_agent.py     # PLCデータ収集エージェント
│   ├── templates/       # WebUI（ラズパイ用）
│   └── config/          # 設定ファイル
├── pages/               # Nuxt.jsページ（中央ダッシュボード）
├── components/          # Vueコンポーネント
│   └── monitoring/      # モニタリング関連コンポーネント（リファクタリング済み）
├── composables/         # Vue Composables
├── scripts/             # 開発・管理スクリプト
├── docker-compose.yml   # Docker Compose設定
└── nuxt.config.ts       # Nuxt.js設定
```

## 🚀 主要機能

### 1. リアルタイムモニタリング
- **Socket.IO**によるリアルタイムデータ配信
- **Chart.js**による高性能グラフ表示（v-memo最適化）
- カード再レンダリングなし、グラフのみスムーズ更新

### 2. ログデータ最適化システム
- **自動データ保存期間管理**: 90日以上古いデータを自動削除
- **階層化アーカイブ**: 日次・月次集計データによる効率的な長期保存
- **パフォーマンス最適化**: インデックス追加によるクエリ高速化

#### データ保存戦略
- **短期データ（90日間）**: 詳細ログデータ、リアルタイム監視用
- **中期データ（1年間）**: 日次集計データ、週次・月次トレンド分析用（圧縮率99.9%）
- **長期データ（永続保存）**: 月次集計データ、年次比較・長期計画用（圧縮率99.99%）

### 3. コンポーネント分割アーキテクチャ
- **MonitoringHeader**: ヘッダー部分（設備情報・接続状態）
- **StatusCards**: ステータスカード・アラート表示
- **ChartCards**: リアルタイムグラフカード
- **DataCards**: 最新データ履歴テーブル
- **MonitoringDebugPanel**: デバッグパネル

## 🏗️ システムアーキテクチャ

```
[工場内LAN: 192.168.1.0/24]

┌─────────────────────────────────────────────┐
│ 中央サーバー兼管理PC (192.168.1.10)          │
│ ├─ PostgreSQL (ポート5432)                  │
│ ├─ Flask Backend (ポート5000)               │
│ ├─ Nuxt UI (ポート3000)                     │
│ └─ デスクトップアプリ                         │
└─────────────────────────────────────────────┘
            ↑ HTTP POST (PLCデータ送信)
            │
┌───────────┼─────────────────────────────┐
│  Raspberry Pi #1    Raspberry Pi #2      │
│  (192.168.1.101)    (192.168.1.102)     │
│  └─ PLCエージェント  └─ PLCエージェント     │
└────┼───────────────────┼─────────────────┘
     │                   │
   [PLC#1]             [PLC#2]
```

## ⚡ クイックスタート

### 中央サーバー起動

```bash
# プロジェクトルートで
cd plc-dashboard

# 環境変数設定
cp .env.example .env

# PostgreSQL + Flask Backend
docker compose up -d db backend

# Nuxt.js Frontend（ポート3000）
npm run dev
```

### Raspberry Piエージェント起動

```bash
cd plc-dashboard/raspi_agent

# ダミーPLCモード（開発用）
export USE_DUMMY_PLC=true
python agent_app.py  # ポート8080
```

### デモデータ送信（開発用）

```bash
cd plc-dashboard/backend
python demo_data_sender.py --mode continuous --interval 2.0
```

ブラウザで `http://localhost:3000/monitoring/LINE_A_001` にアクセス。

## 🛠️ 開発スクリプト

```bash
# Docker環境管理
./scripts/docker-dev.sh start      # 開発環境を起動
./scripts/docker-dev.sh stop       # 開発環境を停止
./scripts/docker-dev.sh logs       # ログを表示

# テスト・検証
python scripts/test_monitoring_chart.py  # モニタリング画面テスト
python scripts/test_e2e_deployment.py    # E2Eテスト
python scripts/quick_verify.py           # 簡易確認

# データベース管理
python scripts/check_security.py         # セキュリティチェック
./scripts/backup_database.sh             # データベースバックアップ
./scripts/restore_database.sh            # データベース復元
```

## 🔧 環境変数設定

### バックエンド（`backend/.env`）

```env
DATABASE_URL=postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Raspberry Piエージェント（`raspi_agent/.env`）

```env
# PLC接続設定
PLC_IP=192.168.0.10
PLC_PORT=5000
PLC_MANUFACTURER=Mitsubishi
LOG_INTERVAL_MS=5000
USE_DUMMY_PLC=false

# エラー処理設定
MAX_RETRY_ATTEMPTS=3
CONNECTION_TIMEOUT=5
READ_TIMEOUT=3

# セキュリティ設定
ALLOWED_PLC_IPS=192.168.0.10,192.168.0.20
READ_ONLY_MODE=true
```

## 📚 ドキュメント

詳細なドキュメントは`_docs/`ディレクトリに体系的に記録されています：

- **`_docs/decisions/`** - 設計判断の根拠
- **`_docs/features/`** - 機能実装の記録
- **`_docs/plc-knowledge/`** - PLC特有の知見
- **`_docs/architecture/`** - コードアーキテクチャ
- **`_docs/deployment/`** - デプロイメント手順
- **`_docs/setup/`** - 環境セットアップ

詳細は `_docs/README.md` を参照してください。

## 🎯 最近のリファクタリング

### コンポーネント分割（2025-10-27）
- `pages/monitoring/[id].vue`（673行）を4つのコンポーネントに分割
- MonitoringHeader、StatusCards、ChartCards、DataCardsを作成
- `useChartManagement_v2.js` → `useChartManagement.js`にリネーム
- Playwrightテスト成功：モニタリング画面が正常に動作

### ディレクトリ整理（2025-10-27）
- すべてのモニタリング関連コンポーネントを`components/monitoring/`に集約
- テストデータファイルを`backend/test_data/`に移動
- 不要なアーカイブファイルを削除

## 🚀 技術スタック

- **Frontend**: Nuxt.js 3 + Vuetify 3 + Chart.js + Socket.IO Client
- **Backend**: Flask + Flask-SocketIO + SQLAlchemy
- **Database**: PostgreSQL（推奨）/ SQLite（フォールバック）
- **Real-time**: Socket.IO（threading mode）
- **Data Collection**: Raspberry Pi + Python（Modbus/FINS通信）

## 📝 ライセンス

MIT License

## 🤝 貢献

プロジェクトへの貢献を歓迎します。詳細は`CONTRIBUTING.md`を参照してください。
