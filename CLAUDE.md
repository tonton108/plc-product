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
6. **作業完了後はローカルで動作確認を行い、その後PRを作成してGitHub ActionsとCodexレビューを確認すること。**

---

## 作業フロー

すべての開発作業は以下のフローに従って進めてください：

### 1. コード変更

機能追加、バグ修正、リファクタリング等を実施

### 2. ローカルで動作確認

変更内容に応じて以下を実施：

#### a) Nuxt UI (フロントエンド) を修正した場合

```bash
# 1. データベース・バックエンド起動
cd plc-dashboard
docker compose up -d db backend

# 2. フロントエンド起動
npm run dev

# 3. デモデータ送信
cd backend
python demo_data_sender.py --mode continuous --interval 2.0
```

**確認項目:**
- ✅ ブラウザで `http://localhost:3000/monitoring/DEMO_001` にアクセス
- ✅ UIが正常に表示されるか
- ✅ リアルタイムデータ更新が動作するか
- ✅ ブラウザコンソールにJavaScriptエラーがないか
- ✅ レイアウト崩れがないか

#### b) Flask Backend (API) を修正した場合

```bash
# 1. データベース起動
cd plc-dashboard
docker compose up -d db

# 2. バックエンド起動（ローカル）
cd backend
flask --app manage.py run

# または Docker で起動
# docker compose up -d backend
```

**確認項目:**
- ✅ サーバーが正常に起動するか（エラーログがないか）
- ✅ APIエンドポイントが正常に動作するか
  - curl/Postman でテスト、または
  - `python demo_data_sender.py --mode single` でデータ送信テスト
- ✅ Socket.IO通信が正常に動作するか
- ✅ 必要に応じてフロントエンドも起動して統合テスト

#### c) Database (マイグレーション/モデル) を修正した場合

```bash
# 1. データベース起動
cd plc-dashboard
docker compose up -d db

# 2. マイグレーション実行
cd backend
flask --app manage.py db upgrade

# 3. テーブル構造確認（必要に応じて）
psql -U plc_user -h localhost -d plc_monitor -c "\d+ logs"

# 4. バックエンド起動
flask --app manage.py run
```

**確認項目:**
- ✅ マイグレーションが正常に完了するか
- ✅ エラーメッセージがないか
- ✅ テーブル構造が期待通りか（カラム追加、インデックス作成等）
- ✅ バックエンドが正常に起動するか
- ✅ 既存データとの互換性があるか

#### d) Raspberry Pi Agent を修正した場合

```bash
# 1. ダミーPLCモードで起動テスト
cd plc-dashboard/raspi_agent
export USE_DUMMY_PLC=true
python agent_app.py  # ポート8080で起動

# 2. ブラウザで初回設定画面を確認
# http://localhost:8080/

# 3. 中央サーバーを起動してデータ送信テスト
cd ../backend
docker compose up -d db
flask --app manage.py run

# 4. エージェントからデータ送信を確認
# ラズパイエージェントのログを確認
```

**確認項目:**
- ✅ エージェントが正常に起動するか
- ✅ PLC通信が正常に動作するか（ダミーモード or 実機）
- ✅ 中央サーバーへのデータ送信が成功するか
- ✅ エラーログがないか
- ✅ タイムアウト・リトライ処理が正しく動作するか
- ✅ エンディアン変換が正しく行われているか（float32, dword等）

### 3. PR作成

- 新しいブランチを作成: `git checkout -b feature/your-feature-name`
- 変更をコミット（日本語コミットメッセージ）
- リモートにプッシュ: `git push -u origin feature/your-feature-name`
- GitHub上でPRを作成

### 4. GitHub ActionsでPlaywrightテスト自動実行

PR作成後、自動的に以下が実行されます：
- PostgreSQL起動
- マイグレーション実行
- バックエンド・フロントエンド起動
- PlaywrightによるE2Eテスト
- スクリーンショット・テスト結果のアップロード

### 5. Codex自動レビュー

PR作成後、自動的にCodex AIがコードレビューを実施します：
- `@codex`メンションが自動投稿される
- `ai-review`ラベルが付与される
- PLC特有の問題（エンディアン、タイムアウト設定等）をチェック
- セキュリティ脆弱性、パフォーマンス問題を検出
- 具体的な修正案をdiff形式で提示

詳細は `_docs/features/codex-auto-review.md` を参照してください。

### 6. 問題なければマージ

- GitHub Actionsのテストが全てパス ✅
- Codexレビューで重大な問題が指摘されていない ✅
- 必要に応じて修正を反映
- `main`ブランチにマージ

---

## プロジェクト概要

このリポジトリには、PLC（Programmable Logic Controller）データの収集・監視・分析システムの**統合版**が含まれています。

### 統合後のプロジェクト構成

**plc-dashboard（メインプロジェクト）**に以下が統合されています:
1. **backend/**: Flask API（中央サーバー）
2. **raspi_agent/**: Raspberry Piエージェント
3. **pages/**: Nuxt.js 3ダッシュボードUI
4. **scripts/**: 開発・管理ツール
5. **docker-compose.yml**: 統合Docker Compose設定

**旧raspi_plc_uiディレクトリは_archive/raspi_plc_ui/にアーカイブされています。現在のシステムではplc-dashboard/raspi_agent/を使用してください。**

### 📚 プロジェクト知識ベース

設計判断や実装の背景、PLC特有の知見は `_docs/` ディレクトリに体系的に記録されています：

- **`_docs/decisions/`** - 設計判断の根拠（なぜSocket.IOをthreadingモードにしたか、など）
- **`_docs/features/`** - 機能実装の記録（Codex自動レビュー、ローカルバッファリング、など）
- **`_docs/plc-knowledge/`** - PLC特有の知見（プロトコル、エンディアン、タイムアウト、トラブルシューティング）
- **`_docs/architecture/`** - コードアーキテクチャの詳細
- **`_docs/deployment/`** - デプロイメント手順
- **`_docs/setup/`** - 環境セットアップ（MCP, CI/CD等）
- **`_docs/commands/`** - 開発コマンド集

詳細は `_docs/README.md` を参照してください。

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
1. Raspberry Pi各台がPLCからデータ収集（Modbus/FINS通信）
2. 収集データを中央サーバーにHTTP POST
3. Flask Backendがデータベースに保存し、WebSocket経由でリアルタイム配信
4. 不特定多数のクライアント端末がNuxt UIにブラウザでアクセスし、リアルタイムモニタリング

詳細は `_docs/architecture/` を参照してください。

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

### PLC知見（plc-knowledge）

PLCプロジェクト特有の実装ノウハウ：

- `_docs/plc-knowledge/protocols.md` - PLCプロトコル実装ガイド（Modbus、FINS、MC Protocol）
- `_docs/plc-knowledge/endianness.md` - エンディアン問題と対処法（Big-Endian必須）
- `_docs/plc-knowledge/timeout-settings.md` - タイムアウト設定のベストプラクティス
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティングガイド

### 機能実装（features）

新機能の実装記録：

- `_docs/features/codex-auto-review.md` - Codex AI自動レビュー機能

### デプロイメント（deployment）

本番環境へのデプロイ手順：

- `_docs/deployment/raspi-deployment.md` - Raspberry Piデプロイメント
- `_docs/deployment/environment-variables.md` - 環境変数設定ガイド

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

詳細は `_docs/decisions/socketio-threading-mode.md` を参照。

### 2. 設備識別の優先順位

**設備識別は以下の優先順位で行ってください：**

1. `cpu_serial_number`（最優先・不変）
2. `mac_address`（準不変）
3. `equipment_id`（可変・ユーザー定義）

詳細は `_docs/decisions/equipment-identification-strategy.md` を参照。

### 3. PLCプロトコル実装

**すべてのPLCでBig-Endianを使用します。**

```python
# ✅ 正しい: Big-Endian
bytes_data = struct.pack('>HH', word1, word2)

# ❌ 間違い: Little-Endian
bytes_data = struct.pack('<HH', word1, word2)
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

---

## Playwrightによる動作確認

**重要:** すべてのPRに対してGitHub ActionsでPlaywrightテストが自動実行されます。PR作成前にローカルで動作確認を行い、基本的な問題を事前に解決してください。

### 自動テスト（GitHub Actions）

PR作成時に以下のE2Eテストが自動実行されます：

- PostgreSQLデータベースの起動とマイグレーション実行
- バックエンド・フロントエンドサーバーの起動
- デモデータの送信
- Playwrightによるブラウザテスト
  - ログイン画面の表示確認
  - モニタリング画面でグラフが表示されるか
  - リアルタイムデータ更新が正常に動作するか
  - JavaScriptエラーが発生していないか
- スクリーンショット・テスト結果のアーティファクト保存

設定ファイル: `.github/workflows/playwright-tests.yml`

### ローカルでの動作確認（推奨）

PR作成前に、変更したコンポーネントに応じて基本的な動作確認を実施してください。

詳細な手順は「## 作業フロー > ### 2. ローカルで動作確認」を参照してください：

- **Nuxt UI (フロントエンド)** を修正した場合 → a) の手順
- **Flask Backend (API)** を修正した場合 → b) の手順
- **Database (マイグレーション/モデル)** を修正した場合 → c) の手順
- **Raspberry Pi Agent** を修正した場合 → d) の手順

---

## トラブルシューティング

問題が発生したら、まず以下を確認してください：

1. **`_docs/plc-knowledge/troubleshooting.md`** - よくある問題と解決策
2. **環境変数設定** - `_docs/deployment/environment-variables.md`
3. **ログ確認** - `docker compose logs -f backend`

---

**最終更新:** 2025-10-24
