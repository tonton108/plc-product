# MCP Server セットアップガイド

このガイドでは、Claude CodeでModel Context Protocol (MCP)サーバーをセットアップする方法を説明します。

## 導入済みMCPサーバー

### 1. PostgreSQL MCP Server
**用途**: PLC監視システムのデータベースに直接アクセスし、SQLクエリを実行してデータを分析

**設定**: `.mcp.json`に設定済み

**接続情報**:
- Database: `plc_monitor`
- User: `plc_user`
- Host: `localhost`
- Port: `5432`

**使用例**:
- "最新10件のPLCログデータを取得して"
- "DEMO_001の過去24時間のデータを集計して"
- "エラー率が5%を超える設備を検索して"

### 2. GitHub MCP Server
**用途**: GitHubリポジトリ、Issue、Pull Requestへのアクセス

**設定**: `.mcp.json`に設定済み（要：GitHub Personal Access Token）

**使用例**:
- "このプロジェクトの未解決Issueを一覧表示して"
- "最新のPull Requestをレビューして"
- "main branchとの差分を確認して"

## セットアップ手順

### 前提条件

1. **Node.jsのインストール**
   ```bash
   # Node.js 18以上が必要
   node --version
   ```

2. **PostgreSQLの起動確認**
   ```bash
   # Docker Composeで起動
   cd plc-dashboard
   docker compose up -d db

   # または、ローカルPostgreSQLが起動していることを確認
   psql -U plc_user -h localhost -d plc_monitor -c "SELECT version();"
   ```

### GitHub Personal Access Tokenの取得

1. GitHubにログイン: https://github.com/settings/tokens

2. **"Generate new token" → "Generate new token (classic)"** をクリック

3. トークン名を入力（例: "Claude Code MCP"）

4. 必要なスコープを選択:
   - ✅ `repo` (リポジトリへのフルアクセス)
   - ✅ `read:org` (組織の読み取り)
   - ✅ `read:user` (ユーザー情報の読み取り)

5. **"Generate token"** をクリック

6. 生成されたトークンをコピー（⚠️ この画面でしか確認できません）

### 環境変数の設定

1. `.env`ファイルを作成（存在しない場合）
   ```bash
   cd plc-dashboard
   cp .env.example .env
   ```

2. `.env`ファイルに`GITHUB_TOKEN`を追加
   ```env
   GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

3. `.env`ファイルを`.gitignore`に追加されていることを確認（既に設定済み）

### Claude Codeでの確認

1. **Claude Codeを再起動**
   - VS Codeを完全に再起動するか
   - Claude Codeウィンドウをリロード

2. **MCPサーバーの状態確認**
   ```
   /mcp
   ```
   以下のように表示されればOK:
   ```
   ✅ postgres - PLC監視システムのPostgreSQLデータベースへの読み取り専用アクセス
   ✅ github - GitHubリポジトリ、Issue、Pull Requestへのアクセス
   ```

3. **接続テスト**
   ```
   # PostgreSQL接続テスト
   "設備一覧を取得して"

   # GitHub接続テスト
   "このリポジトリの最新コミットを確認して"
   ```

## トラブルシューティング

### PostgreSQL MCPが接続できない

**症状**: `Error: connection refused`

**解決方法**:
1. PostgreSQLが起動しているか確認
   ```bash
   docker compose ps
   ```

2. 接続情報が正しいか確認
   ```bash
   psql -U plc_user -h localhost -d plc_monitor
   ```

3. `.mcp.json`の接続URLを確認
   ```json
   "postgresql://plc_user:plc_pass@localhost:5432/plc_monitor"
   ```

### GitHub MCPが認証エラーになる

**症状**: `Error: Bad credentials` または `401 Unauthorized`

**解決方法**:
1. GitHub Personal Access Tokenが正しく設定されているか確認
   ```bash
   # .envファイルを確認
   grep GITHUB_TOKEN .env
   ```

2. トークンの有効期限を確認
   - https://github.com/settings/tokens

3. 必要なスコープ（repo, read:org, read:user）が付与されているか確認

4. トークンを再生成して`.env`ファイルを更新

### npxコマンドが見つからない

**症状**: `command not found: npx`

**解決方法**:
1. Node.jsをインストール
   ```bash
   # Windows: https://nodejs.org/
   # macOS: brew install node
   # Linux: sudo apt install nodejs npm
   ```

2. インストール確認
   ```bash
   node --version
   npm --version
   npx --version
   ```

## セキュリティ上の注意

1. **GitHub Tokenの管理**
   - `.env`ファイルを絶対にGitにコミットしない
   - トークンは最小限のスコープで作成
   - 定期的にトークンをローテーション（更新）

2. **PostgreSQL接続情報**
   - `.mcp.json`にはパスワードがハードコードされているため、プロジェクト外に公開しない
   - 本番環境では環境変数を使用する設定に変更を検討
   ```json
   "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
   ```

3. **読み取り専用アクセス**
   - PostgreSQL MCPは読み取り専用として動作
   - 書き込み操作が必要な場合は専用のAPIエンドポイント経由で実行

## 使用例

### PostgreSQL MCPでのデータ分析

```
# 最新のPLCデータを確認
"logsテーブルから最新10件のデータを取得して、設備IDとタイムスタンプ、データ項目を表示して"

# エラー率の高い設備を検索
"過去7日間でエラーが発生した設備を抽出し、エラー率を計算して"

# 日次集計データの確認
"2025年1月の日次集計データを取得して、設備別に平均値を表示して"
```

### GitHub MCPでのリポジトリ管理

```
# 未解決Issueの確認
"このプロジェクトの未解決Issueを一覧表示して、優先度が高いものから順に"

# コミット履歴の確認
"過去1週間のコミット履歴を表示して、誰が何を変更したか確認して"

# Pull Requestのレビュー
"最新のPull Requestの差分を確認して、コードレビューして"
```

## 今後の拡張

以下のMCPサーバーも導入を検討できます：

### Sentry MCP
**用途**: エラー監視、本番環境のデバッグ

**設定方法**:
1. Sentryアカウントを作成: https://sentry.io/
2. プロジェクトを作成
3. Auth Tokenを取得
4. `.mcp.json`に追加:
   ```json
   "sentry": {
     "command": "uvx",
     "args": ["mcp-server-sentry", "--auth-token", "${SENTRY_TOKEN}"],
     "env": {},
     "description": "Sentryエラーモニタリング"
   }
   ```

### Notion MCP
**用途**: ドキュメント管理、PLC設定・マニュアルの整理

**設定方法**:
1. Notion Integration APIを作成
2. `.mcp.json`に追加（設定方法はNotion公式ドキュメント参照）

---

## 参考リンク

- [Model Context Protocol 公式ドキュメント](https://modelcontextprotocol.io/)
- [Claude Code MCP ガイド](https://docs.claude.com/en/docs/claude-code/mcp)
- [PostgreSQL MCP Server](https://www.npmjs.com/package/@modelcontextprotocol/server-postgres)
- [GitHub MCP Server](https://www.npmjs.com/package/@modelcontextprotocol/server-github)
