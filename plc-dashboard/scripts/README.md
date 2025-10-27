# Scripts ディレクトリ

開発・テスト・運用に使用するスクリプト集

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

## アーカイブ

### `archive/old_tests/`
開発中に使用した古いテストスクリプト

### `archive/screenshots/`
テスト実行時に生成されたスクリーンショット

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
