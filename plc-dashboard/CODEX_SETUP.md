# Codex自動レビュー セットアップガイド

このガイドでは、OpenAI Codex（ChatGPT Plus付属）を使用してGitHub Pull Requestの自動コードレビューをセットアップする方法を説明します。

## 前提条件

- ✅ **ChatGPT Plus契約**（$20/月）
- ✅ GitHubアカウント
- ✅ GitHubリポジトリへのアクセス権

## Codexとは

Codexは、OpenAIが提供するAIコードレビューエージェントです。GPT-5-Codexモデル（192,000トークンのコンテキストウィンドウ）を使用し、バグ、セキュリティリスク、スタイルの問題を88%の精度で検出します。

**主な機能:**
- Pull Requestの自動レビュー
- セキュリティ脆弱性の検出
- パフォーマンス問題の指摘
- コード品質の改善提案
- 192Kトークンの超大規模コンテキスト

## セットアップ手順

### ステップ1: ChatGPT Plusでの確認

1. **ChatGPTにログイン**
   - https://chat.openai.com/

2. **Codexが有効か確認**
   - Settings → Beta Features
   - "Codex" が有効になっているか確認
   - 無効の場合は有効化

### ステップ2: GitHubとの連携

1. **ChatGPT設定からGitHub連携**
   - Settings → Integrations
   - "GitHub" を追加
   - リポジトリへのアクセスを許可

2. **権限の確認**
   - リポジトリの読み取り権限
   - PRへのコメント権限

### ステップ3: GitHub Actionsの設定（自動化）

このリポジトリには既に`.github/workflows/codex-review.yml`が設定されています。

**動作:**
- PRが作成/更新されると自動的にCodexレビューをトリガー
- `@codex review`コメントを自動投稿
- `ai-review`ラベルを自動付与

### ステップ4: 手動レビュー（オプション）

GitHub Actions経由の自動レビュー以外に、PRコメントから手動でレビューを依頼することもできます。

**基本的なレビュー依頼:**
```
@codex review
```

**具体的な観点を指定:**
```
@codex review for security vulnerabilities
```

**複数の観点を指定:**
```
@codex review this PR for:
- Security vulnerabilities
- Performance issues
- PLC communication bugs
- Python best practices
```

**日本語でレビューを依頼:**
```
@codex review in Japanese
```

## PLCプロジェクト専用のレビュー観点

このプロジェクト用にカスタマイズされたレビュー観点:

```
@codex review this PR for:
- Security vulnerabilities (especially in PLC communication)
- PLC protocol implementation (Modbus TCP, FINS, MC Protocol)
- Endianness issues (all PLCs use Big-Endian)
- Error handling and timeout settings
- Python type safety and best practices
- Performance issues
- Code quality and maintainability

Please provide feedback in Japanese (日本語でレビューしてください).
```

## CI/CDパイプラインとの統合

### GitHub Actions（自動実行）

このリポジトリには以下のワークフローが設定されています:

#### 1. `ci.yml` - 基本的なCI/CD
- **Backend Tests**: pytest + coverage（カバレッジ85%以上）
- **Linting**: pylint, black（コードフォーマット）
- **Frontend Tests**: Nuxt.js build + ESLint
- **Security Scan**: Trivy脆弱性スキャン
- **Docker Build**: Docker Compose ビルドテスト

#### 2. `codex-review.yml` - Codex自動レビュー
- PRが作成されると自動的にCodexレビューをトリガー
- PLCプロジェクト特有の観点でレビュー
- 日本語でのフィードバック

### ワークフローの動作確認

```bash
# PRを作成してCI/CDをテスト
git checkout -b test/my-feature
# 変更を加える
git add .
git commit -m "test: 新機能のテスト"
git push origin test/my-feature

# GitHub上でPR作成
# → 自動的にCodexレビューがトリガーされる
```

## Codexレビューの例

### 良い例: Codexが検出する問題

#### セキュリティ問題
```python
# 問題のあるコード
plc_password = "admin123"  # ハードコードされたパスワード

# Codexの指摘
# ❌ セキュリティリスク: パスワードをハードコードしないでください
# ✅ 推奨: 環境変数から読み込む
plc_password = os.getenv("PLC_PASSWORD")
```

#### エンディアン問題
```python
# 問題のあるコード
addr_bytes = b'\x00' + addr_num.to_bytes(2, byteorder='big')

# Codexの指摘
# ❌ アドレスバイト順序が不正です
# ✅ FINSプロトコル仕様: word_address(2 bytes) + bit_position(1 byte)
addr_bytes = addr_num.to_bytes(2, byteorder='big') + b'\x00'
```

#### タイムアウト設定
```python
# 問題のあるコード
plc.connect(ip, port)  # タイムアウト無し

# Codexの指摘
# ⚠️ タイムアウト設定が無いため、接続が永遠に待機する可能性
# ✅ 推奨: 3-5秒のタイムアウトを設定
plc.settimeout(3.0)
plc.connect(ip, port)
```

## トラブルシューティング

### Codexが反応しない

**症状**: `@codex review`とコメントしても反応がない

**解決方法:**
1. ChatGPT PlusでCodexが有効か確認
2. GitHubとの連携が正しく設定されているか確認
3. リポジトリへのアクセス権限を確認
4. 数分待ってから再試行（Codexの処理には時間がかかる場合がある）

### GitHub Actionsが失敗する

**症状**: CI/CDワークフローが失敗する

**解決方法:**
1. Actionsタブでエラーログを確認
2. 依存関係の問題: `requirements.txt`を確認
3. テストカバレッジが85%未満: テストを追加
4. Lintエラー: `black`や`pylint`を実行して修正

### Codexのレビューが英語で返ってくる

**症状**: 日本語でレビューを依頼したが、英語で返ってくる

**解決方法:**
```
@codex review this PR in Japanese. 日本語でレビューしてください。
```

### レビューの精度が低い

**症状**: Codexが間違った指摘をする

**解決方法:**
1. より具体的なレビュー観点を指定
2. プロジェクト固有のコンテキストを提供
3. `.codex/context.md`ファイルを作成してプロジェクト情報を記載

## ベストプラクティス

### 1. 小さなPRを作成

- **推奨**: 変更が200行以内
- **理由**: Codexが全体を理解しやすく、精度が高い

### 2. 具体的なレビュー観点を指定

- ❌ `@codex review`（漠然としている）
- ✅ `@codex review for security and PLC communication issues`

### 3. テストを充実させる

- Codexはテストコードも評価します
- テストカバレッジが高いほど、レビューの質が向上

### 4. CI/CDと組み合わせる

- Codexレビュー + 自動テスト + Linting
- 人間がレビューする前にAIで品質を保証

## コスト

### ChatGPT Plus（$20/月）
- Codex機能含む
- 追加コスト無し
- 無制限のレビュー

### 追加オプション（検討中）
- **CodeRabbit**: +$15-30/月（より詳細な静的解析）
- **Bugbot**: +$40/月（Cursor IDE統合）
- **Devin**: +$500/月（自動修正エージェント）

現時点では**Codex単独（$20/月、追加コスト無し）**で開始し、効果を見てから追加を検討します。

## 次のステップ

### 1. テストPRで動作確認
```bash
git checkout -b test/codex-test
echo "# Codexテスト" >> README.md
git add README.md
git commit -m "test: Codex自動レビューの動作確認"
git push origin test/codex-test
```

GitHub上でPR作成 → Codexが自動レビュー

### 2. 実際の開発で使用

- 新機能追加時にPR作成
- Codexレビュー → 修正 → CI/CD通過
- 人間レビュー → マージ

### 3. 効果を測定

- レビュー時間の短縮
- バグ検出率の向上
- コード品質の向上

### 4. 追加ツール検討（1-2週間後）

効果が確認できたら:
- CodeRabbitの追加検討
- Devinによる自動修正の導入検討

---

## 参考リンク

- [OpenAI Codex公式ドキュメント](https://openai.com/codex/)
- [ChatGPT Plus](https://openai.com/chatgpt/pricing/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [PLCプロジェクトCI/CDガイド](./MCP_SETUP.md)

---

## まとめ

✅ **ChatGPT Plus契約で追加コスト無し**
✅ **GitHub Actionsで自動化済み**
✅ **PLCプロジェクト専用の観点設定済み**
✅ **今すぐ使える状態**

まずはテストPRを作成して、Codexの自動レビューを体験してみてください！
