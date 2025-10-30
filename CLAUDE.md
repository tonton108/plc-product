# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Claude Code 会話ルール（日本語モード固定）

- Claudeはすべての**会話・提案・説明・コメント**を**日本語**で行うこと。
- コード内コメントも可能な限り日本語で記述すること。
- 英語での説明が含まれる場合は、日本語訳を併記すること。
- CLI出力やログ文言も、特別な理由がなければ日本語で提案すること。
- 回答の際は、過剰な翻訳ではなく技術的な正確さを優先すること。

Claudeは以下のルールを厳守すること：

1. すべてのコミットメッセージは**日本語**で書くこと。
2. 英語は使わず、要約を1行で簡潔に。
3. フォーマットは「タイプ: 概要」形式（例：`refactor: 古いディレクトリを整理し重複を解消`）。
4. Claude Codeは**自動署名（🤖やCo-Authored行）を付与しないこと。**
5. 英語が混ざった場合は即座に修正し、再コミット前に確認を求めること。

---

## 作業フロー

### 基本フロー

1. **コード変更**
2. **ローカル動作確認**（コンポーネント別）
3. **コミット作成**
4. **PR作成**
5. **GitHub Actions実行**（自動テスト）
6. **Codexレビュー**（自動または手動）
7. **マージ**

### コンポーネント別ローカル動作確認

#### a. Nuxt UI変更時

```bash
# 1. 開発サーバー起動
cd plc-dashboard
npm run dev

# 2. ブラウザで動作確認（http://localhost:3000）

# 3. Playwrightテスト実行（推奨）
python scripts/test_monitoring_chart.py
```

#### b. Flask Backend変更時

```bash
# 1. バックエンド起動
cd plc-dashboard/backend
flask --app manage.py run

# 2. APIエンドポイントを確認
curl http://localhost:5000/api/equipment

# 3. データベースマイグレーション（モデル変更時）
flask --app manage.py db migrate -m "変更内容"
flask --app manage.py db upgrade
```

#### c. Database変更時

```bash
# 1. マイグレーション作成
cd plc-dashboard/backend
flask --app manage.py db migrate -m "変更内容"

# 2. マイグレーション適用
flask --app manage.py db upgrade

# 3. テーブル確認
python check_tables.py
```

#### d. Raspberry Piエージェント変更時

```bash
# 1. ダミーPLCモードで起動
cd plc-dashboard/raspi_agent
export USE_DUMMY_PLC=true
python agent_app.py

# 2. WebUI確認（http://localhost:5001）

# 3. データ送信テスト
python ../backend/demo_data_sender.py --mode single
```

**重要:** 作業完了前に必ずPlaywrightで動作確認を行うこと。

---

## プロジェクト概要

このリポジトリには、PLC（Programmable Logic Controller）データの収集・監視・分析システムの**統合版**が含まれています。

### アーキテクチャ構成

- **フロントエンド**: Nuxt.js 3 + Vuetify 3 + Chart.js + Socket.IO Client
- **バックエンド**: Flask + Flask-SocketIO + SQLAlchemy
- **データベース**: PostgreSQL（推奨・本番環境・開発環境共通）
- **リアルタイム通信**: Socket.IO（threading mode）
- **データ収集**: Raspberry Pi + Python（PLCとModbus/FINS/MC Protocol通信）

**重要:** このプロジェクトでは**PostgreSQLを優先して使用**してください。SQLiteはフォールバック用ですが、開発環境でもPostgreSQLを使用することを強く推奨します。

### 統合後のプロジェクト構成

**plc-dashboard（メインプロジェクト）**に以下が統合されています:
1. **backend/**: Flask API（中央サーバー）
2. **raspi_agent/**: Raspberry Piエージェント
3. **pages/**: Nuxt.js 3ダッシュボードUI
4. **scripts/**: 開発・管理ツール
5. **docker-compose.yml**: 統合Docker Compose設定

**旧raspi_plc_uiディレクトリは_archive/raspi_plc_ui/にアーカイブされています。現在のシステムではplc-dashboard/raspi_agent/を使用してください。**

### システムアーキテクチャ（イントラネット環境）

このシステムは**工場内LAN等のイントラネット環境**での利用を想定しています。

```
[工場内LAN: 例 192.168.1.0/24]

┌─────────────────────────────────────────────┐
│ 中央サーバー兼管理PC (例: 192.168.1.10)      │
│ ├─ PostgreSQL (ポート5432)                  │
│ ├─ Flask Backend (ポート5000)               │
│ ├─ Nuxt UI (ポート3000) ※不特定多数に公開   │
│ └─ デスクトップアプリ ※管理者用             │
└─────────────────────────────────────────────┘
            ↑ HTTP POST (PLCデータ送信)
            │
┌───────────┼─────────────────────────────┐
│  Raspberry Pi #1    Raspberry Pi #2      │
│  (例: 192.168.1.101) (192.168.1.102)     │
│  ├─ raspi_agent     ├─ raspi_agent       │
│  └─ PLC #1に接続    └─ PLC #2に接続      │
│     ↑ Modbus/FINS      ↑ Modbus/FINS     │
└────┼───────────────────┼─────────────────┘
     │                   │
   [PLC#1]             [PLC#2]

            ↑ ブラウザで http://192.168.1.10:3000 にアクセス
            │
┌───────────┴─────────────────────────────┐
│  クライアント端末（不特定多数）            │
│  ├─ 現場PC・管理PC (Windows/Mac/Linux)   │
│  ├─ タブレット (iPad/Android)            │
│  └─ スマートフォン (iOS/Android)         │
└──────────────────────────────────────────┘
```

**データフロー:**
1. Raspberry Pi各台がPLCからデータ収集（Modbus/FINS/MC Protocol通信）
2. 収集データを中央サーバーにHTTP POST
3. Flask Backendがデータベースに保存し、WebSocket経由でリアルタイム配信
4. 不特定多数のクライアント端末がNuxt UIにブラウザでアクセスし、リアルタイムモニタリング

### 📚 プロジェクト知識ベース

設計判断や実装の背景、PLC特有の知見は `_docs/` ディレクトリに体系的に記録されています：

- **`_docs/decisions/`** - 設計判断の根拠（なぜSocket.IOをthreadingモードにしたか、など）
- **`_docs/features/`** - 機能実装の記録（Codex自動レビュー、ローカルバッファリング、など）
- **`_docs/plc-knowledge/`** - PLC特有の知見（プロトコル、エンディアン、タイムアウト、トラブルシューティング）
- **`_docs/architecture/`** - コードアーキテクチャの詳細
- **`_docs/deployment/`** - デプロイメント手順
- **`_docs/setup/`** - 環境セットアップ（MCP, CI/CD等）
- **`_docs/commands/`** - 開発コマンド集
- **`_docs/testing/`** - テスト・デバッグガイド

詳細は `_docs/README.md` を参照してください。

---

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

### デモデータ送信（開発用）

```bash
cd plc-dashboard/backend
python demo_data_sender.py --mode continuous --interval 2.0
```

ブラウザで `http://localhost:3000/monitoring/DEMO_001` にアクセスしてリアルタイムデータを確認。

詳細は `_docs/commands/development.md` を参照してください。

---

## 主要ドキュメント

### 設計判断（decisions）

なぜその技術・設計を選んだのか、判断理由を記録：

- `_docs/decisions/socketio-threading-mode.md` - Socket.IO threading mode選択理由
- `_docs/decisions/equipment-identification-strategy.md` - 設備識別の優先順位戦略
- `_docs/decisions/data-archiving-strategy.md` - 階層化アーカイブシステム
- `_docs/decisions/query-optimization.md` - クエリ最適化戦略
- `_docs/decisions/performance-optimization.md` - パフォーマンス最適化施策

### アーキテクチャ（architecture）

コード構造と主要ファイルの詳細：

- `_docs/architecture/backend.md` - バックエンド（Flask）詳細
- `_docs/architecture/frontend.md` - フロントエンド（Nuxt.js）詳細
- `_docs/architecture/raspi-agent.md` - Raspberry Piエージェント詳細
- `_docs/architecture/database.md` - データベース設計詳細
- `_docs/architecture/realtime-communication.md` - リアルタイム通信実装詳細

### PLC知見（plc-knowledge）

PLCプロジェクト特有の実装ノウハウ：

- `_docs/plc-knowledge/protocols.md` - PLCプロトコル実装ガイド（Modbus、FINS、MC Protocol）
- `_docs/plc-knowledge/endianness.md` - エンディアン問題と対処法（Big-Endian必須）
- `_docs/plc-knowledge/timeout-settings.md` - タイムアウト設定のベストプラクティス
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティングガイド
- `_docs/plc-knowledge/plc-manufacturers.md` - 対応メーカーとプロトコル一覧

### 機能実装（features）

新機能の実装記録：

- `_docs/features/codex-auto-review.md` - Codex AI自動レビュー機能

### デプロイメント（deployment）

本番環境へのデプロイ手順：

- `_docs/deployment/raspi-deployment.md` - Raspberry Piデプロイメント
- `_docs/deployment/environment-variables.md` - 環境変数設定ガイド

### テスト（testing）

テストとデバッグの詳細：

- `_docs/testing/debugging-guide.md` - テスト・デバッグガイド

### セットアップ（setup）

開発環境・CI/CDのセットアップ：

- `_docs/setup/mcp-servers.md` - MCP Server設定
- `_docs/setup/ci-cd.md` - CI/CDセットアップ

### 開発コマンド（commands）

日常的に使う開発コマンド集：

- `_docs/commands/development.md` - 開発コマンド集

---

## 重要な注意点

### 1. Socket.IO初期化

**必ず`async_mode='threading'`で初期化してください。**

```python
# plc-dashboard/backend/app.py
socketio.init_app(app, async_mode='threading', cors_allowed_origins="*")
```

**理由:** Greenletエラーを回避し、Flaskとの互換性を確保するため。

詳細は `_docs/decisions/socketio-threading-mode.md` を参照。

### 2. 設備識別の優先順位

**設備識別は以下の優先順位で行ってください：**

1. `cpu_serial_number`（最優先・不変）- Raspberry PiのCPUシリアル番号
2. `mac_address`（準不変）- MACアドレス
3. `equipment_id`（可変・ユーザー定義）

```python
# routes.py:388-432 参照
equipment = Equipment.query.filter_by(cpu_serial_number=cpu_serial_number).first()
if equipment:
    equipment.equipment_id = equipment_id  # 設備IDを新しい値に更新
```

詳細は `_docs/decisions/equipment-identification-strategy.md` を参照。

### 3. PLCプロトコル実装

**すべてのPLCでBig-Endianを使用します。**

```python
# ✅ 正しい: Big-Endian
bytes_data = struct.pack('>HH', word1, word2)

# ❌ 間違い: Little-Endian
bytes_data = struct.pack('<HH', word1, word2)
```

**三菱PLCのfloat32/dword読み取り例:**

```python
# raspi_agent/plc_agent.py:442-463 参照
# 2ワード読み取り (32bit)
word_values = plc.batchread_wordunits(headdevice="D100", readsize=2)

# Big-Endian形式で結合
word1, word2 = word_values[0], word_values[1]
combined = (word1 << 16) | word2
float_value = struct.unpack('>f', struct.pack('>I', combined))[0]  # '>f' = Big-Endian
```

詳細は `_docs/plc-knowledge/endianness.md` を参照。

### 4. タイムアウト設定

**PLC通信は必ずタイムアウト（3-5秒）を設定してください。**

```python
# ✅ 正しい
plc.connect(ip, port, timeout=5.0)

# ❌ 間違い
plc.connect(ip, port)
```

詳細は `_docs/plc-knowledge/timeout-settings.md` を参照。

### 5. 変数シャドーイング問題

**問題:** ループ変数に`config`という名前を使用すると、グローバル変数`config`をシャドーイングしてUnboundLocalErrorが発生します。

```python
# ❌ 悪い例（変数シャドーイング）
config = load_config()
for config in plc_configs:  # グローバルのconfigをシャドーイング
    process(config)

# ✅ 良い例
config = load_config()
for plc_config in plc_configs:  # 別の変数名を使用
    process(plc_config)
```

**実装箇所:** `raspi_agent/agent_app.py:236-271`

---

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

詳細は `_docs/testing/debugging-guide.md` を参照。

---

## トラブルシューティング

問題が発生したら、まず以下を確認してください：

### 1. データベース接続エラー

```bash
# PostgreSQL接続確認
psql -U plc_user -h localhost -d plc_monitor -c "SELECT version();"

# PostgreSQLの起動状態確認
docker compose ps db

# マイグレーション実行
cd backend
flask --app manage.py db upgrade
```

### 2. Socket.IO接続エラー

- CORSオリジン設定を確認（`backend/app.py:18-20, 60`）
- ポート5000が開いているか確認

```bash
# ポート確認
lsof -i :5000

# バックエンドログで確認
docker compose logs -f backend
```

### 3. データが表示されない

```bash
# 1. データが保存されているか確認
curl http://localhost:5000/api/logs/DEMO_001/latest

# 2. Socket.IOイベント受信確認（ブラウザコンソール）

# 3. Flaskログでデータ受信・配信を確認
docker compose logs -f backend | grep "📡 WebSocket"
```

### 4. 詳細なトラブルシューティング

以下のドキュメントを参照してください：

- `_docs/testing/debugging-guide.md` - テスト・デバッグガイド
- `_docs/plc-knowledge/troubleshooting.md` - PLCトラブルシューティング

---

## ドキュメント更新ルール

このセクションでは、作業完了時にCLAUDE.mdと_docs/を更新するためのガイドラインを提供します。

詳細は `_docs/DOCUMENT_MAINTENANCE.md` を参照してください。

### 更新が必要なケース

以下の変更を行った場合、**必ず該当ドキュメントを更新**してください：

| 変更内容 | 更新対象ドキュメント |
|---------|-------------------|
| 新しいAPIエンドポイント追加 | `_docs/architecture/backend.md` |
| データベースモデル変更 | `_docs/architecture/database.md` |
| マイグレーション追加 | `_docs/architecture/database.md` |
| 新しいPLCメーカー対応 | `_docs/plc-knowledge/plc-manufacturers.md` |
| プロトコル実装追加 | `_docs/plc-knowledge/protocols.md` |
| 新機能追加 | `_docs/features/[機能名].md`（新規作成） |
| 設計判断 | `_docs/decisions/[判断内容].md`（新規作成） |
| 作業フロー変更 | `CLAUDE.md` |
| 環境変数追加 | `_docs/deployment/environment-variables.md` |

### 更新が不要なケース

以下の変更では**ドキュメント更新は不要**です：

- バグ修正（ロジック変更なし）
- コメント追加・修正
- リファクタリング（機能・API変更なし）
- テストコード追加
- ログ出力の変更
- 変数名変更（外部APIに影響なし）

---

**最終更新:** 2025-10-30
