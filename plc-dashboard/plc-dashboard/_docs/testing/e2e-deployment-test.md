# E2Eデプロイメントテスト手順書

このドキュメントでは、ラズパイから中央サーバーまでのデータフロー全体を統合的にテストする手順を説明します。

## 概要

このテストでは、以下のシナリオを検証します：

1. ✅ **Docker環境の確認** - Docker Desktopが起動しているか
2. ✅ **ポートの確認** - 必要なポート（5433, 5000, 3000, 5001）が使用可能か
3. ✅ **中央サーバーの起動** - Docker Composeで DB + Backend + Frontend を起動
4. ✅ **Backend APIのヘルスチェック** - APIが正常に応答しているか
5. ✅ **Frontend UIのヘルスチェック** - UIが正常に表示されるか
5.5. ✅ **Frontend UI実レンダリングテスト（Playwright）** - JavaScriptエラーがないか実際のブラウザで検証（2025-01追加）
6. ✅ **Raspberry Pi Agentの起動** - ダミーPLCモードでエージェントを起動
7. ✅ **データフローの確認** - Agent → Backend → Frontend のデータ送信
8. ✅ **モニタリング画面の確認** - リアルタイムデータが表示されているか

---

## 前提条件

### 必要なソフトウェア

- ✅ Docker Desktop (Windows/Mac)
- ✅ Python 3.8以上
- ✅ Node.js 18以上（Frontendビルド用）

### 必要なPythonパッケージ

```bash
# 必須
pip install requests

# オプション（Frontend実レンダリングテスト用）
pip install playwright
playwright install chromium  # 約150MB
```

**Playwrightについて**:
- 完全無料（Apache 2.0ライセンス）
- ヘッドレスブラウザでJavaScriptエラーを自動検出
- インストールしなくてもテストは実行可能（該当ステップがスキップされます）

---

## テスト実行手順

### 1. プロジェクトルートに移動

```bash
cd D:\plc-product\plc-dashboard
```

### 2. 環境変数を設定（初回のみ）

`.env`ファイルが存在しない場合は作成します：

```bash
# Windowsの場合
copy .env.example .env

# Linux/Macの場合
cp .env.example .env
```

### 3. E2Eテストスクリプトを実行

```bash
python scripts/test_e2e_deployment.py
```

### 4. テストの進行

スクリプトは以下の順序で自動的に実行されます：

#### STEP 1-2: 環境確認

```
[STEP 1] Docker環境の確認
✓ Dockerが起動しています

[STEP 2] ポートの確認
✓ ポート5433は使用可能です（PostgreSQL）
✓ ポート5000は使用可能です（Backend API）
✓ ポート3000は使用可能です（Frontend UI）
✓ ポート5001は使用可能です（Raspberry Pi Agent）
```

**ポートが使用中の場合**:
- 既存のプロセスを停止するか、ポート番号を変更してください
- Dockerサービスは `docker compose down` で停止できます

#### STEP 3: Docker Composeサービス起動

```
[STEP 3] 中央サーバーの起動（Docker Compose）
ℹ サービスを起動中...
ℹ   - PostgreSQL (ポート5433)
ℹ   - Flask Backend (ポート5000)
ℹ   - Nuxt Frontend (ポート3000)
✓ Docker Composeサービスが起動しました
ℹ 起動完了を待機中... (30秒)
```

**エラーが発生した場合**:
```bash
# ログを確認
docker compose logs -f backend
docker compose logs -f frontend

# 再起動
docker compose restart backend frontend
```

#### STEP 4-5: ヘルスチェック

```
[STEP 4] Backend APIのヘルスチェック
ℹ 接続試行 1/10...
✓ Backend APIが正常に応答しています

[STEP 5] Frontend UIのヘルスチェック
ℹ 接続試行 1/10...
✓ Frontend UIが正常に応答しています
```

**タイムアウトする場合**:
- Dockerコンテナが正常に起動しているか確認: `docker ps`
- リソース不足の場合はDocker Desktopのリソース設定を調整

#### STEP 5.5: Frontend UI 実レンダリングテスト（Playwright）

**このステップは2025-01に追加されました。**

従来のHTTPヘルスチェックでは、HTMLレスポンスのみを確認していましたが、実際のJavaScriptの実行やレンダリングは検証していませんでした。Playwrightを使用することで、ヘッドレスブラウザで実際にページを開き、以下を自動検証できます：

- ✅ JavaScriptが正常に実行されるか
- ✅ ページが正しくレンダリングされるか
- ✅ コンソールエラーが発生していないか
- ✅ スクリーンショットを自動保存（証拠として）

```
[STEP 5.5] Frontend UI の実レンダリングテスト（Playwright）
[INFO] ヘッドレスブラウザでページを開いています...
[INFO] http://localhost:3000/ にアクセス中...
[INFO] ページのレンダリングを待機中...
[OK] ページが正しくレンダリングされました
[INFO] スクリーンショット保存: D:\plc-product\plc-dashboard\scripts\frontend_test_screenshot.png
[OK] JavaScriptエラーなし
```

**Playwrightのインストール（初回のみ）**:

```bash
# Playwrightをインストール
pip install playwright

# Chromiumブラウザをインストール（約150MB）
playwright install chromium
```

**完全無料**: Playwrightはオープンソース（Apache 2.0ライセンス）で、商用利用も含めて完全無料です。

**エラーが発生した場合**:
- スクリーンショットが保存されるので、`frontend_error_screenshot.png`を確認してください
- JavaScriptエラーの詳細がコンソールに出力されます
- Nuxtのビルドログを確認: `docker logs plc-frontend --tail 100`

**Playwrightがインストールされていない場合**:
- このステップは自動的にスキップされ、警告メッセージが表示されます
- テストは続行されますが、JavaScriptエラーは検出されません

#### STEP 6: Raspberry Pi Agent起動（手動）

```
[STEP 6] Raspberry Pi Agent の起動
ℹ ダミーPLCモードでエージェントを起動中...
⚠ このテストでは、エージェントを手動で起動してください:
ℹ   cd D:\plc-product\plc-dashboard\raspi_agent
ℹ   set USE_DUMMY_PLC=true
ℹ   set CENTRAL_SERVER_IP=localhost
ℹ   set CENTRAL_SERVER_PORT=5000
ℹ   python agent_app.py

エージェントを起動したら、Enterキーを押してください...
```

**別のターミナルで実行**:

```bash
# 新しいターミナルを開く
cd D:\plc-product\plc-dashboard\raspi_agent

# 環境変数を設定（Windows）
set USE_DUMMY_PLC=true
set CENTRAL_SERVER_IP=localhost
set CENTRAL_SERVER_PORT=5000

# エージェントを起動
python agent_app.py
```

**期待される出力**:
```
====================================
   Raspberry Pi PLC エージェント
====================================

設定読み込み完了
設備ID: テスト１１１
PLC IP: 192.168.0.100
動作モード: ダミーPLCモード

Flaskアプリケーション起動中...
 * Running on http://0.0.0.0:5001
```

エージェントが起動したら、元のターミナルに戻り **Enter** を押します。

#### STEP 7: Raspberry Pi Agentのヘルスチェック

```
[STEP 7] Raspberry Pi Agent のヘルスチェック
ℹ 接続試行 1/5...
✓ Raspberry Pi Agentが正常に応答しています
```

#### STEP 8: データフローの確認

```
[STEP 8] データフローのテスト
ℹ 設備一覧を取得中...
✓ 設備一覧取得成功: 1件
ℹ 設備 'テスト１１１' の最新ログを取得中...
✓ 最新ログ取得成功:
ℹ   設備ID: テスト１１１
ℹ   タイムスタンプ: 2025-10-26T15:30:45
ℹ   データ項目:
ℹ     - temperature: 25.5
ℹ     - pressure: 1013.25
ℹ     - production_count: 1234
```

**データが取得できない場合**:
1. Raspberry Pi Agentが正常に動作しているか確認
2. Backend APIログを確認: `docker compose logs -f backend`
3. データベースに接続できているか確認

#### STEP 9: モニタリング画面の確認

```
[STEP 9] モニタリング画面の確認
✓ 以下のURLでモニタリング画面を確認できます:
ℹ   http://localhost:3000/monitoring/テスト１１１

ℹ モニタリング画面で以下を確認してください:
ℹ   1. リアルタイムデータがグラフに表示されている
ℹ   2. データが定期的に更新されている（2-5秒間隔）
ℹ   3. WebSocket接続が確立されている（画面右上に接続ステータス表示）
```

**ブラウザで確認**:
1. `http://localhost:3000/monitoring/テスト１１１` を開く
2. リアルタイムグラフが表示されることを確認
3. データが自動的に更新されることを確認（2-5秒ごと）

#### テスト結果サマリー

```
======================================================================
  テスト結果サマリー
======================================================================
  Docker環境: ✓
  ポート確認: ✓
  Docker起動: ✓
  Backend API: ✓
  Frontend UI: ✓
  Raspberry Pi Agent: ✓
  データフロー: ✓

======================================================================
  テスト成功
======================================================================
✓ すべてのテストが正常に完了しました

ℹ 次のステップ:
ℹ   1. モニタリング画面でリアルタイムデータを確認
ℹ   2. 設備設定画面でPLCデータ項目を設定
ℹ   3. 履歴データを確認
```

---

## クリーンアップ

テスト終了後、サービスを停止します：

```
======================================================================
  クリーンアップ
======================================================================

Docker Composeサービスを停止しますか？ (y/n): y
ℹ サービスを停止中...
✓ サービスを停止しました
⚠ Raspberry Pi Agentは手動で停止してください（Ctrl+C）
```

**手動でクリーンアップする場合**:

```bash
# Docker Composeサービスを停止
docker compose down

# Raspberry Pi Agentを停止（エージェントのターミナルで Ctrl+C）
```

---

## トラブルシューティング

### Docker起動エラー

**症状**: `Dockerが起動していません`

**解決策**:
1. Docker Desktopを起動する
2. タスクマネージャーでDockerサービスが実行中か確認
3. Dockerを再起動: Docker Desktop → Restart

### ポート競合エラー

**症状**: `ポート5000は既に使用中です`

**解決策**:

```bash
# ポートを使用しているプロセスを確認（Windows）
netstat -ano | findstr :5000

# プロセスを停止
taskkill /PID <PID番号> /F

# または、既存のDockerサービスを停止
docker compose down
```

### Backend API接続エラー

**症状**: `Backend APIに接続できません`

**解決策**:

```bash
# Backendコンテナの状態を確認
docker ps | grep backend

# Backendログを確認
docker compose logs -f backend

# Backendコンテナを再起動
docker compose restart backend

# データベースマイグレーション実行
docker compose exec backend flask --app manage.py db upgrade
```

### Raspberry Pi Agent起動エラー

**症状**: エージェントが起動しない

**解決策**:

```bash
# 依存パッケージをインストール
cd plc-dashboard/raspi_agent
pip install -r requirements.txt

# 設定ファイルを確認
cat config/plc_config.json

# ログファイルを確認
cat plc_agent.log
```

### データが表示されない

**症状**: モニタリング画面にデータが表示されない

**解決策**:

1. **Backendログを確認**:
```bash
docker compose logs -f backend
```

2. **設備が登録されているか確認**:
```bash
# ブラウザで設備一覧を確認
http://localhost:3000

# APIで直接確認
curl http://localhost:5000/api/equipment
```

3. **WebSocket接続を確認**:
- ブラウザの開発者ツール（F12）を開く
- Consoleタブでエラーメッセージを確認
- NetworkタブでWebSocket接続を確認

---

## 次のステップ

テストが成功したら、以下の手順で実際の運用環境にデプロイします：

1. **本番用環境変数を設定** - `_docs/deployment/environment-variables.md` を参照
2. **Raspberry Piにデプロイ** - `_docs/deployment/raspi-deployment.md` を参照
3. **実際のPLCに接続** - `USE_DUMMY_PLC=false` に変更し、PLC設定を更新
4. **セキュリティ設定** - IPホワイトリスト、読み取り専用モード等を設定

---

## 関連ドキュメント

- [開発コマンド集](_docs/commands/development.md) - 日常的な開発コマンド
- [アーキテクチャ概要](_docs/architecture/backend.md) - システム構成の詳細
- [トラブルシューティング](_docs/plc-knowledge/troubleshooting.md) - よくある問題と解決策
- [デプロイメント手順](_docs/deployment/raspi-deployment.md) - 本番環境へのデプロイ

---

**最終更新**: 2025-10-26
