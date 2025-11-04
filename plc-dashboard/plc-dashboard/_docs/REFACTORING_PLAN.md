# CLAUDE.md リファクタリング計画

**作成日:** 2025-10-24

## 現状分析

### CLAUDE.md
- **総行数:** 646行
- **問題点:** Claude Codeが読み込むには長すぎる（理想: 200行以内）
- **内容:** プロジェクト概要、詳細な実装ノウハウ、コマンド集、トラブルシューティングが混在

### _docs
- **状況:** 基本構造は完成、一部ドキュメント作成済み
- **不足:** アーキテクチャ、デプロイ、セットアップ系のドキュメント

---

## 設計方針

### CLAUDE.mdの役割（目標: 200行以内）

**位置づけ:** Claude Codeが最初に読む「地図」

**残すべき内容:**
1. ✅ Claude Code 会話ルール（日本語モード固定）
2. ✅ プロジェクト概要（簡潔に）
3. ✅ システムアーキテクチャ図
4. ✅ 📚 プロジェクト知識ベース（_docsへのポインタ）
5. ✅ クイックスタート（開発コマンドの要約）
6. ✅ 主要ドキュメントへのリンク集

**削除する内容（_docsへ移動）:**
- ❌ 詳細なコードアーキテクチャ説明
- ❌ データベース設計の詳細
- ❌ デプロイメント手順の詳細
- ❌ トラブルシューティング詳細
- ❌ 重要な実装上の注意点（コードレベル）
- ❌ パフォーマンス最適化の詳細
- ❌ MCP Server詳細設定
- ❌ CI/CD詳細設定

### _docsの役割

**位置づけ:** 詳細な知識ベース

**追加すべきディレクトリ:**
- `_docs/architecture/` - コードアーキテクチャの詳細
- `_docs/deployment/` - デプロイメント手順
- `_docs/setup/` - 環境セットアップ（MCP, CI/CD等）
- `_docs/commands/` - 開発コマンド集

---

## 移動計画

### 1. アーキテクチャ → `_docs/architecture/`

**現在のCLAUDE.md:321-469（149行）**
```
## コードアーキテクチャ
### plc-dashboard（中央サーバー）
#### backend/app.py
#### backend/api/routes.py
...
```

**移動先:**
- `_docs/architecture/backend.md` - バックエンドアーキテクチャ
- `_docs/architecture/frontend.md` - フロントエンドアーキテクチャ
- `_docs/architecture/raspi-agent.md` - Raspberry Piエージェント

### 2. データベース設計 → `_docs/decisions/`

**現在のCLAUDE.md:478-491（14行）**
```
## データベース設計
### 階層化アーカイブシステム
### 最適化インデックス
```

**移動先:**
- `_docs/decisions/data-archiving-strategy.md` - データアーカイブ戦略

### 3. デプロイメント → `_docs/deployment/`

**現在のCLAUDE.md:493-533（41行）**
```
## デプロイメント
### ラズパイへの一括デプロイ
### 環境変数設定
```

**移動先:**
- `_docs/deployment/raspi-deployment.md` - ラズパイデプロイ
- `_docs/deployment/environment-variables.md` - 環境変数設定

### 4. トラブルシューティング → `_docs/plc-knowledge/`

**現在のCLAUDE.md:534-561（28行）**
```
## トラブルシューティング
### Socket.IO Greenletエラー
### 設備が見つからない
...
```

**移動先:**
- ✅ すでに `_docs/plc-knowledge/troubleshooting.md` に統合済み
- CLAUDE.mdからは削除して、リンクのみ残す

### 5. 重要な実装上の注意点 → `_docs/decisions/`

**現在のCLAUDE.md:596-632（37行）**
```
## 重要な実装上の注意点
### 設備の識別と更新
### データ最適化クエリ
### PLCデータ読み取りのフォールバック
```

**移動先:**
- ✅ 設備識別 → すでに `_docs/decisions/equipment-identification-strategy.md` に作成済み
- `_docs/decisions/query-optimization.md` - クエリ最適化戦略（新規作成）
- ✅ フォールバック → すでに `_docs/plc-knowledge/protocols.md` に記載済み

### 6. パフォーマンス最適化 → `_docs/decisions/`

**現在のCLAUDE.md:634-646（13行）**
```
## パフォーマンス最適化
### データベース最適化効果
### データ圧縮率
```

**移動先:**
- `_docs/decisions/performance-optimization.md` - パフォーマンス最適化戦略（新規作成）

### 7. MCP Server詳細 → `_docs/setup/`

**現在のCLAUDE.md:170-211（42行）**
```
## MCP Serverの導入と活用
### 導入済みMCPサーバー
...
```

**移動先:**
- `_docs/setup/mcp-servers.md` - MCP Server設定（新規作成）

### 8. CI/CD詳細 → `_docs/setup/`

**現在のCLAUDE.md:212-320（109行）**
```
## CI/CDとAI自動レビュー
### GitHub Actions CI/CD
### Codex AI自動レビュー
...
```

**移動先:**
- `_docs/setup/ci-cd.md` - CI/CDセットアップ（新規作成）
- ✅ Codex → すでに `_docs/features/codex-auto-review.md` に作成済み

### 9. 開発コマンド → `_docs/commands/`

**現在のCLAUDE.md:94-169（76行）**
```
## 開発コマンド
### 統合プロジェクト（plc-dashboard）
### バックエンド（Flask）
...
```

**移動先:**
- `_docs/commands/development.md` - 開発コマンド集（新規作成）

---

## 作業手順

### Step 1: 不足している_docsドキュメントを作成

1. `_docs/architecture/backend.md`
2. `_docs/architecture/frontend.md`
3. `_docs/architecture/raspi-agent.md`
4. `_docs/decisions/data-archiving-strategy.md`
5. `_docs/decisions/query-optimization.md`
6. `_docs/decisions/performance-optimization.md`
7. `_docs/deployment/raspi-deployment.md`
8. `_docs/deployment/environment-variables.md`
9. `_docs/setup/mcp-servers.md`
10. `_docs/setup/ci-cd.md`
11. `_docs/commands/development.md`

### Step 2: CLAUDE.mdをスリム化

新しいCLAUDE.md構成（目標: 200行以内）:

```markdown
# CLAUDE.md

## Claude Code 会話ルール（日本語モード固定）
（現状のまま）

## プロジェクト概要
（簡潔に - 統合後のプロジェクト構成のみ）

### 📚 プロジェクト知識ベース
（現状のまま - _docsへの参照）

### システムアーキテクチャ
（図のみ残す、詳細は_docs/architecture/へ）

## クイックスタート

### 中央サーバー起動
```bash
cd plc-dashboard
docker compose up -d db backend
npm run dev
```

### Raspberry Piエージェント起動
```bash
cd plc-dashboard/raspi_agent
python agent_app.py
```

詳細は `_docs/commands/development.md` を参照。

## 主要ドキュメント

### 設計判断
- `_docs/decisions/socketio-threading-mode.md` - Socket.IO設定
- `_docs/decisions/equipment-identification-strategy.md` - 設備識別
- `_docs/decisions/data-archiving-strategy.md` - データアーカイブ
- `_docs/decisions/query-optimization.md` - クエリ最適化
- `_docs/decisions/performance-optimization.md` - パフォーマンス

### アーキテクチャ
- `_docs/architecture/backend.md` - バックエンド詳細
- `_docs/architecture/frontend.md` - フロントエンド詳細
- `_docs/architecture/raspi-agent.md` - Raspberry Piエージェント

### PLC知見
- `_docs/plc-knowledge/protocols.md` - プロトコル実装
- `_docs/plc-knowledge/endianness.md` - エンディアン問題
- `_docs/plc-knowledge/timeout-settings.md` - タイムアウト設定
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティング

### 機能実装
- `_docs/features/codex-auto-review.md` - Codex自動レビュー

### デプロイメント
- `_docs/deployment/raspi-deployment.md` - ラズパイデプロイ
- `_docs/deployment/environment-variables.md` - 環境変数

### セットアップ
- `_docs/setup/mcp-servers.md` - MCP Server設定
- `_docs/setup/ci-cd.md` - CI/CD設定

### 開発コマンド
- `_docs/commands/development.md` - 開発コマンド集
```

### Step 3: 動作確認

- [ ] Claude Codeがスリム化されたCLAUDE.mdを読めるか
- [ ] _docsへのリンクが正しく機能するか
- [ ] 必要な情報がすべて_docsに移動できているか

---

## 期待される効果

### CLAUDE.md（200行以内）
- ✅ Claude Codeが高速に読み込み
- ✅ プロジェクト全体像を一目で把握
- ✅ 詳細は_docsへのリンクで参照

### _docs（体系的な知識ベース）
- ✅ 詳細な実装ノウハウを蓄積
- ✅ 設計判断の根拠を記録
- ✅ トラブルシューティング手順を整理

---

**最終更新:** 2025-10-24
