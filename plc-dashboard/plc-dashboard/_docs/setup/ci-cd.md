# CI/CDセットアップガイド

**作成日:** 2025-10-24

## GitHub Actions CI/CD

このプロジェクトではGitHub Actionsを使用して自動テスト・Lint・セキュリティスキャンを実行します。

### ワークフロー

`.github/workflows/ci.yml` - 基本的なCI/CD

**実行内容:**
- Backend Tests: pytest + coverage（カバレッジ45%以上、目標85%）
- Linting: pylint, black
- Frontend Tests: Nuxt.js build + ESLint
- Security Scan: Trivy脆弱性スキャン
- Docker Build: ビルドテスト

**自動実行:**
- Pull Request作成時
- masterブランチへのpush時

### テストカバレッジの現状と改善計画

現在のカバレッジ: **46%**（2025年1月時点）
- ✅ PLCドライバー層: 高カバレッジ（94-99%）
- ✅ ローカルバッファ: 75%
- ❌ アプリケーション層: 0%（`agent_app.py`, `plc_agent.py`）

**段階的な改善計画:**
1. **第1段階（現在）:** 閾値45% - CI/CDの基盤確立
2. **第2段階:** 閾値60% - `agent_app.py`の基本APIエンドポイントテストを追加
3. **第3段階:** 閾値75% - `plc_agent.py`のメインループ、エラーハンドリングのテストを追加
4. **第4段階:** 閾値85% - 統合テスト、エッジケースのテストを追加

## Codex AI自動レビュー

詳細は `_docs/features/codex-auto-review.md` を参照してください。

### ワークフロー

`.github/workflows/codex-review.yml` - Codex自動レビュー

**実行内容:**
- PR作成時に自動レビュー依頼
- PLCプロジェクト特有の観点（セキュリティ、エンディアン、タイムアウト等）
- 日本語でのフィードバック
- 具体的なコード修正案の提示

### セットアップ方法

詳細は `plc-dashboard/CODEX_SETUP.md` を参照してください。

**前提条件:**
- ChatGPT Plus契約（$20/月、追加コスト無し）
- GitHubとの連携設定
- MFA（多要素認証）の有効化

### 使用例

```bash
# PRを作成
git checkout -b feature/my-feature
# 変更を加える
git add .
git commit -m "feat: 新機能追加"
git push origin feature/my-feature

# GitHub上でPR作成
# → 自動的にCI/CDとCodexレビューがトリガーされる
```

## 将来の拡張（検討中）

効果を確認後、以下のツールも追加検討:
- **CodeRabbit:** より詳細な静的解析（+$15-30/月）
- **Bugbot:** Cursor IDE統合（+$40/月）
- **Devin:** AI自動修正エージェント（+$500/月）

---

**最終更新:** 2025-10-24
