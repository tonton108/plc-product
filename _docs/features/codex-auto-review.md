# Codex自動レビュー機能

**作成日:** 2025-10-24
**実装日:** 2025-01-15
**ステータス:** 実装完了 ✅

## 目的

PR作成時に自動的にCodex（ChatGPT）がコードレビューを行い、PLC特有の問題を早期発見する。

## 実装内容

### ワークフローファイル

`.github/workflows/codex-review.yml`

**トリガー:**
- PRが`main`ブランチに作成・更新されると自動実行

**処理:**
1. PRコメントに`@codex`メンションを投稿
2. `ai-review`ラベルを付与
3. Codexが自動的にレビューコメントを返信

### レビュー観点

- セキュリティ脆弱性（PLC通信セキュリティ）
- PLCプロトコル実装（Modbus TCP、FINS、MC Protocol）
- **エンディアン問題**（全PLCでBig-Endian）
- エラーハンドリング・タイムアウト設定
- Pythonベストプラクティス
- パフォーマンス問題

### 修正案提示機能

**実装日:** 2025-10-24

問題を発見した場合、diff形式で具体的な修正案を提示します。

## 技術的な実装ポイント

### 日本語レビュー依頼

```yaml
reviewComment: |
  @codex review this PR in Japanese. 日本語でレビューしてください.

  **重要**: 問題を発見した場合は、具体的なコード修正案を提示してください。
  修正前後のコードを diff 形式で示してください。
```

### PLC特有の観点

Codexに明示的にPLC特有の問題をチェックさせます：

- `Endianness issues (all PLCs use Big-Endian)`
- `PLC protocol implementation (Modbus TCP, FINS, MC Protocol)`
- `Error handling and timeout settings`

## 完了条件

- [x] PR作成時に自動的に`@codex`メンションが投稿される
- [x] `ai-review`ラベルが自動付与される
- [x] Codexが日本語でレビューコメントを返信する
- [x] 具体的な修正案がdiff形式で提示される

## リスク

### 誤検知の可能性

Codexが誤った指摘をする可能性があります。最終判断は開発者が行ってください。

### API制限

ChatGPT Plusの利用規約に準拠してください。過度なPR作成はAPI制限に引っかかる可能性があります。

## 関連ファイル

- `.github/workflows/codex-review.yml:1-59` - ワークフロー定義
- `plc-dashboard/CODEX_SETUP.md` - セットアップガイド
- CLAUDE.md:236-300 - 使用方法

## 関連ドキュメント

- `_docs/plc-knowledge/endianness.md` - エンディアン問題
- `_docs/plc-knowledge/timeout-settings.md` - タイムアウト設定

---

**最終更新:** 2025-10-24
