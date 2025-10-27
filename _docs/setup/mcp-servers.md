# MCP Server セットアップガイド

**作成日:** 2025-10-24
**最終更新:** 2025-10-25

## 概要

Model Context Protocol (MCP) サーバーを使用して、Claude CodeからデータベースやGitHubリポジトリ、その他の開発ツールに直接アクセスできます。

このガイドでは、PLCモニタリングシステム開発で特に有効なMCPサーバーのセットアップ方法を説明します。

---

## 🎯 推奨MCPサーバー

このプロジェクトで特に役立つMCPサーバー：

| MCPサーバー | 用途 | 優先度 |
|-----------|------|--------|
| PostgreSQL | データベースクエリ・分析 | ⭐⭐⭐ 必須 |
| GitHub | リポジトリ操作・Issue管理 | ⭐⭐⭐ 必須 |
| Docker | コンテナ管理・ログ確認 | ⭐⭐ 推奨 |
| Sentry | エラー監視・デバッグ | ⭐⭐ 推奨 |
| Socket Security | 依存関係セキュリティチェック | ⭐ 任意 |

---

## 📦 セットアップ手順

### 前提条件

- Node.js 18以上がインストールされていること
- Claude Codeがインストールされていること

```bash
# Node.jsバージョン確認
node --version  # v18.0.0以上
```

### 1. PostgreSQL MCP Server（⭐⭐⭐ 必須）

**用途:** PLC監視システムのデータベースに自然言語でクエリ実行

#### グローバル設定（推奨）

```bash
# MCPサーバーを追加
claude mcp add --transport stdio postgres \
  --env POSTGRES_HOST=localhost \
  --env POSTGRES_PORT=5432 \
  --env POSTGRES_DATABASE=plc_monitoring \
  --env POSTGRES_USER=your_user \
  --env POSTGRES_PASSWORD=your_password \
  -- npx -y @modelcontextprotocol/server-postgres
```

#### プロジェクト個別設定

`plc-dashboard/.mcp.json` を作成：

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DATABASE": "plc_monitoring",
        "POSTGRES_USER": "plc_user",
        "POSTGRES_PASSWORD": "your_secure_password"
      }
    }
  }
}
```

**環境変数ファイルで管理（推奨）:**

`plc-dashboard/.env.mcp` を作成：

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=plc_monitoring
POSTGRES_USER=plc_user
POSTGRES_PASSWORD=your_secure_password
```

`.mcp.json` で参照：

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "envFile": ".env.mcp"
    }
  }
}
```

**セキュリティ注意:**
```bash
# .gitignoreに追加
echo ".env.mcp" >> .gitignore
```

#### 使用例

```
「過去24時間のPLCログデータを取得して」
「DEMO_001の平均CPU使用率を計算して」
「エラー率が5%を超える設備をリストアップして」
「equipment_masterテーブルの構造を確認して」
```

---

### 2. GitHub MCP Server（⭐⭐⭐ 必須）

**用途:** GitHubリポジトリ、Issue、Pull Requestへのアクセス

#### Personal Access Token発行

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" をクリック
3. 必要なスコープを選択：
   - `repo` (フルアクセス)
   - `read:org` (Organization情報)
   - `workflow` (GitHub Actions)
4. トークンをコピー

#### セットアップ

```bash
# MCPサーバーを追加
claude mcp add --transport stdio github \
  --env GITHUB_TOKEN=ghp_xxxxxxxxxxxx \
  -- npx -y @modelcontextprotocol/server-github
```

または `.mcp.json` に追加：

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx"
      }
    }
  }
}
```

**推奨:** トークンは `.env.mcp` で管理

```bash
# .env.mcp
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

#### 使用例

```
「未解決のIssueを一覧表示して」
「最新のPull Requestの差分を確認して」
「Socket.IO関連の過去のコミット履歴を調べて」
「新しいIssueを作成して: タイトル "PLC通信タイムアウト改善"」
```

---

### 3. Docker MCP Server（⭐⭐ 推奨）

**用途:** コンテナ状態確認・ログ取得・イメージ管理

#### セットアップ

```bash
# MCPサーバーを追加
claude mcp add --transport stdio docker -- npx -y @modelcontextprotocol/server-docker
```

または `.mcp.json` に追加：

```json
{
  "mcpServers": {
    "docker": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-docker"]
    }
  }
}
```

#### 使用例

```
「実行中のコンテナを一覧表示して」
「backendコンテナのログを確認して」
「postgresコンテナの状態を確認して」
「停止しているコンテナを削除して」
```

---

### 4. Sentry MCP Server（⭐⭐ 推奨）

**用途:** 本番環境のエラー監視・デバッグ

#### セットアップ

1. Sentryアカウントを作成（https://sentry.io/）
2. プロジェクトを作成
3. Auth Tokenを発行

```bash
# MCPサーバーを追加
claude mcp add --transport http sentry https://sentry.io/api/mcp
```

#### 使用例

```
「過去24時間のエラーログを分析して」
「最も多く発生しているエラーを特定して」
「PLC通信エラーの詳細を確認して」
```

---

### 5. Socket Security MCP（⭐ 任意）

**用途:** 依存関係のセキュリティチェック

#### セットアップ

```bash
# Socket.devアカウント作成後
claude mcp add --transport http socket https://socket.dev/api/mcp
```

#### 使用例

```
「package.jsonの依存関係をスキャンして」
「セキュリティ脆弱性をチェックして」
```

---

## 🔧 統合設定ファイル例

### `plc-dashboard/.mcp.json`（完全版）

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "envFile": ".env.mcp"
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "docker": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-docker"]
    }
  }
}
```

### `plc-dashboard/.env.mcp`

```bash
# PostgreSQL接続情報
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=plc_monitoring
POSTGRES_USER=plc_user
POSTGRES_PASSWORD=your_secure_password

# GitHub Personal Access Token
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Sentry設定（オプション）
SENTRY_DSN=https://xxxx@sentry.io/xxxx
SENTRY_AUTH_TOKEN=xxxx
```

**重要:** `.env.mcp` を `.gitignore` に追加してください！

---

## 🚀 接続確認

### Claude Code内で確認

```bash
# MCPサーバー一覧を表示
/mcp

# 接続状態を確認
claude mcp list
```

### 動作テスト

```
Claude Codeで以下を試してください：

1. PostgreSQL:
   「equipment_masterテーブルの全レコード数を教えて」

2. GitHub:
   「このリポジトリの最新コミットを表示して」

3. Docker:
   「実行中のコンテナを確認して」
```

---

## 🎯 プロジェクト固有の活用例

### シナリオ1: デバッグ作業

```
開発者: 「DEMO_001でエラーが発生している原因を調査して」

Claude Code:
1. PostgreSQLで最近のエラーログを検索
2. Dockerでbackendコンテナのログを確認
3. GitHubで関連する変更履歴を調査
4. 原因を特定して修正案を提示
```

### シナリオ2: データ分析

```
開発者: 「先週の稼働率レポートを作成して」

Claude Code:
1. PostgreSQLで先週のplc_logsを集計
2. 設備ごとの稼働率を計算
3. グラフ用のJSONデータを生成
4. 結果をMarkdownレポートで出力
```

### シナリオ3: コード改善

```
開発者: 「Socket.IO実装を最適化して」

Claude Code:
1. GitHubでSocket.IO関連のコードを検索
2. _docs/decisions/socketio-threading-mode.mdを参照
3. 既存実装を分析
4. 最適化案を提示して実装
```

---

## 🛠️ トラブルシューティング

### PostgreSQL接続エラー

```bash
# データベースが起動しているか確認
docker compose ps

# ポート確認
netstat -an | grep 5432

# 接続テスト
psql -h localhost -U plc_user -d plc_monitoring
```

**よくある原因:**
- データベースコンテナが起動していない
- ポート5432が他のサービスで使用されている
- 認証情報が間違っている

### GitHub認証エラー

```bash
# トークンの権限を確認
# repo, read:org, workflow スコープが必要

# トークンの有効期限を確認
# GitHub → Settings → Developer settings → Personal access tokens
```

### npxコマンドが見つからない

```bash
# Node.jsをインストール
# Windows: https://nodejs.org/
# Mac: brew install node
# Linux: sudo apt install nodejs npm

# 確認
node --version
npm --version
```

### MCPサーバーが認識されない

```bash
# Claude Codeを再起動
# .mcp.jsonの構文エラーをチェック
# JSON Validatorで検証: https://jsonlint.com/

# ログ確認（Claude Code）
# Settings → View Logs → MCP Connection
```

---

## 📚 参考リソース

- [Claude Code MCP公式ドキュメント](https://docs.claude.com/en/docs/claude-code/mcp)
- [Model Context Protocol仕様](https://modelcontextprotocol.io/)
- [PostgreSQL MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
- [Docker MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/docker)

---

**最終更新:** 2025-10-25
