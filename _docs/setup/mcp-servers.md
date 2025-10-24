# MCP Server セットアップガイド

**作成日:** 2025-10-24

## 概要

Model Context Protocol (MCP) サーバーを使用して、Claude CodeからデータベースやGitHubリポジトリに直接アクセスできます。

## 導入済みMCPサーバー

### 1. PostgreSQL MCP Server

**用途:** PLC監視システムのデータベースに直接SQLクエリを実行

**設定ファイル:** `plc-dashboard/.mcp.json`

**使用例:**
- "最新10件のPLCログデータを取得して"
- "DEMO_001の過去24時間のデータを集計して"
- "エラー率が5%を超える設備を検索して"

### 2. GitHub MCP Server

**用途:** GitHubリポジトリ、Issue、Pull Requestへのアクセス

**必要な設定:** GitHub Personal Access Token（`.env`ファイルに`GITHUB_TOKEN`を設定）

**使用例:**
- "このプロジェクトの未解決Issueを一覧表示して"
- "最新のPull Requestをレビューして"
- "main branchとの差分を確認して"

## セットアップ方法

詳細なセットアップ手順は `plc-dashboard/MCP_SETUP.md` を参照してください。

**クイックスタート:**
1. Node.js 18以上をインストール
2. `.env`ファイルを作成して`GITHUB_TOKEN`を設定
3. Claude Codeを再起動
4. `/mcp`コマンドで接続状態を確認

## トラブルシューティング

- **PostgreSQL接続エラー:** データベースが起動しているか確認（`docker compose ps`）
- **GitHub認証エラー:** Personal Access Tokenが正しく設定されているか確認（`.env`ファイル）
- **npxコマンドが見つからない:** Node.jsをインストール

詳細は `plc-dashboard/MCP_SETUP.md` を参照してください。

---

**最終更新:** 2025-10-24
