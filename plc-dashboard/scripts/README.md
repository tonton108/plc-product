# Scripts ディレクトリ

開発・テスト・運用に使用するスクリプト集

## Docker環境管理

### `docker-dev.sh`
Docker開発環境の管理スクリプト

```bash
./scripts/docker-dev.sh start      # 開発環境を起動
./scripts/docker-dev.sh stop       # 開発環境を停止
./scripts/docker-dev.sh restart    # 開発環境を再起動
./scripts/docker-dev.sh logs       # 全体のログを表示
./scripts/docker-dev.sh backend-logs   # バックエンドのログを表示
./scripts/docker-dev.sh frontend-logs  # フロントエンドのログを表示
./scripts/docker-dev.sh clean      # Docker環境をクリーンアップ
./scripts/docker-dev.sh shell-backend  # バックエンドコンテナにアクセス
./scripts/docker-dev.sh shell-frontend # フロントエンドコンテナにアクセス
```

## 本番運用スクリプト

### `check_security.py`
セキュリティ設定をチェック（デフォルトパスワード使用の検出）

```bash
python scripts/check_security.py
```

### `check_data.py`
データベース内のデータを確認

```bash
python scripts/check_data.py
```

### `init_db.py`
データベースを初期化

```bash
python scripts/init_db.py
```

## テスト・検証スクリプト

### `test_monitoring_chart.py`
モニタリング画面のグラフ更新をPlaywrightでテスト

```bash
python scripts/test_monitoring_chart.py
```

- カードが再レンダリングされないことを確認
- グラフだけがスムーズに更新されることを確認
- スクリーンショットを自動保存

### `test_e2e_deployment.py`
E2Eデプロイメントテスト（統合テスト）

```bash
python scripts/test_e2e_deployment.py
```

- Docker環境の確認
- サービスの起動と接続確認
- データフローの検証

### `test_db_connection.py`
データベース接続テスト

```bash
python scripts/test_db_connection.py
```

### `quick_verify.py`
アプリケーションの簡易確認（Playwright）

```bash
python scripts/quick_verify.py
```

## 前提条件

### Playwright
一部のテストスクリプトはPlaywrightを使用します。

```bash
pip install playwright
playwright install chromium
```

### Python依存関係
```bash
pip install -r ../backend/requirements.txt
```
