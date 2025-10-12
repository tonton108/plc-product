# PLC監視システム統合完了サマリー

## 統合概要

`plc-dashboard`と`raspi_plc_ui`の2つのプロジェクトを統合し、単一のプロジェクト構成にまとめました。

## 統合前の構成

```
plc-product/
├── plc-dashboard/          # Nuxt.js + Flask（中央サーバー）
│   ├── backend/
│   ├── pages/
│   └── ...
└── raspi_plc_ui/           # Flask + PLCエージェント（ラズパイ）
    ├── backend/
    ├── main.py
    ├── plc_agent.py
    └── ...
```

**問題点:**
- 2つのプロジェクトが独立しており、コード重複が発生
- バックエンドコードが2箇所に存在
- デプロイ・メンテナンスが複雑

## 統合後の構成

```
plc-product/
├── plc-dashboard/          # 統合プロジェクト（メイン）
│   ├── backend/           # Flask API（共通バックエンド）
│   │   ├── api/
│   │   ├── db/
│   │   └── manage.py
│   ├── raspi_agent/       # Raspberry Piエージェント
│   │   ├── agent_app.py  # Flask WebUI（旧main.py）
│   │   ├── plc_agent.py  # PLCデータ収集
│   │   ├── db_utils.py   # ローカル設定管理
│   │   ├── templates/    # WebUI（ラズパイ用）
│   │   ├── config/       # 設定ファイル
│   │   ├── scp_bulk_push.sh
│   │   └── Dockerfile.agent
│   ├── pages/            # Nuxt.jsページ（中央ダッシュボード）
│   ├── components/       # Vueコンポーネント
│   ├── plugins/          # Nuxt.jsプラグイン
│   ├── docker-compose.yml   # 統合Docker Compose
│   ├── .env.example         # 環境変数テンプレート
│   ├── README_INTEGRATED.md # 統合版README
│   └── check_integration.sh # 統合確認スクリプト
└── raspi_plc_ui/         # 旧プロジェクト（参考用に保持）
```

**改善点:**
- バックエンドコードが単一の`backend/`に統合
- `raspi_agent/`が`backend/`を参照し、コード重複を解消
- Docker Composeで両モードを管理
- 環境変数とドキュメントを統一

## 統合内容

### 1. ディレクトリ構造の統合

| 旧ファイル（raspi_plc_ui） | 新ファイル（plc-dashboard） |
|-------------------------|---------------------------|
| `main.py` | `raspi_agent/agent_app.py` |
| `plc_agent.py` | `raspi_agent/plc_agent.py` |
| `db_utils.py` | `raspi_agent/db_utils.py` |
| `templates/` | `raspi_agent/templates/` |
| `config/` | `raspi_agent/config/` |
| `scp_bulk_push.sh` | `raspi_agent/scp_bulk_push.sh` |
| `requirements.txt` | `raspi_agent/requirements_agent.txt` |

### 2. バックエンドの統合

- `plc-dashboard/backend/`を共通バックエンドとして使用
- `raspi_agent/agent_app.py`から`backend/`をインポート
- Docker Composeで`backend/`ディレクトリをraspi-agentコンテナにマウント

### 3. Docker環境の統合

**新しいdocker-compose.yml:**
- `db`: PostgreSQL（共通データベース）
- `backend`: Flask API（中央サーバー）
- `raspi-agent`: Raspberry Piエージェント（`--profile agent`で起動）

### 4. ドキュメントの整備

- `README_INTEGRATED.md`: 統合版の使用方法
- `CLAUDE.md`: 統合版の技術仕様（更新済み）
- `check_integration.sh`: 統合確認スクリプト
- `.env.example`: 環境変数テンプレート

## 起動方法

### 中央サーバーモード

```bash
cd plc-dashboard

# 環境設定
cp .env.example .env

# データベース + バックエンドAPI起動
docker compose up -d db backend

# フロントエンド起動
npm run dev
```

**アクセス:**
- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:5000

### Raspberry Piエージェントモード

```bash
cd plc-dashboard

# エージェント起動（Docker）
docker compose --profile agent up -d raspi-agent

# または、ローカルPythonで起動
cd raspi_agent
python agent_app.py
```

**アクセス:**
- エージェントWebUI: http://localhost:5001

## デプロイメント

### ラズパイへのデプロイ

```bash
cd plc-dashboard/raspi_agent

# ip_list.csvに対象IPを記載
echo "192.168.0.101" >> ip_list.csv

# 一括デプロイ
bash scp_bulk_push.sh
```

## 検証

### 統合確認スクリプト

```bash
cd plc-dashboard
bash check_integration.sh
```

すべてのディレクトリとファイルが✅であることを確認してください。

### 動作確認

1. **中央サーバー:**
```bash
cd plc-dashboard
docker compose up -d db backend
npm run dev
# http://localhost:3000 にアクセス
```

2. **エージェント:**
```bash
cd plc-dashboard/raspi_agent
export USE_DUMMY_PLC=true
python agent_app.py
# http://localhost:5001 にアクセス
```

3. **データフロー確認:**
```bash
# デモデータ送信
cd plc-dashboard/backend
python demo_data_sender.py --mode continuous

# ダッシュボードでリアルタイムデータを確認
# http://localhost:3000/monitoring/DEMO_001
```

## 今後の運用

### 開発

- **中央サーバー開発**: `plc-dashboard/`で作業
- **エージェント開発**: `plc-dashboard/raspi_agent/`で作業
- **共通バックエンド修正**: `plc-dashboard/backend/`で作業（両モードに影響）

### 旧raspi_plc_uiディレクトリ

- 参考用として保持
- 新規開発・本番運用では`plc-dashboard/raspi_agent/`を使用

## 統合のメリット

1. **コードの一元管理**: バックエンドコードが単一の場所に集約
2. **メンテナンス性向上**: 修正が1箇所で済む
3. **デプロイ簡素化**: 単一のDocker Compose設定
4. **ドキュメント統一**: README、CLAUDE.mdが統合され、わかりやすい
5. **開発効率向上**: プロジェクト間の移動が不要

## 注意事項

- 旧`raspi_plc_ui/`ディレクトリは削除せず保持（参考用）
- 既存のラズパイにデプロイ済みの環境は、再デプロイが必要
- 環境変数は`.env.example`を参照して設定

## サポート

統合に関する質問や問題がある場合は、開発者にご連絡ください。
