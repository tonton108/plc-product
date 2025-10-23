# PLCエージェント テストスイート

このディレクトリには、PLCエージェントのユニットテストと統合テストが含まれています。

## テストファイル構成

### 新規テスト（pytestベース）
- `test_plc_drivers_base.py` - plc_drivers.baseモジュールのユニットテスト
  - アドレス解析機能
  - バッチ読み取り最適化
  - ダミーデータ生成

### 既存テスト（スタンドアロン）
- `test_buffer.py` - ローカルバッファリング機能のテスト
- `test_buffer_quick.py` - バッファリングの簡易テスト
- `test_buffer_simple.py` - バッファリングのシンプルテスト
- `test_cpu_serial.py` - CPUシリアル番号取得テスト
- `test_integration.py` - 統合テスト
- `test_load_simulation.py` - 負荷テスト

## テスト実行方法

### 必要な依存関係のインストール

```bash
pip install pytest pytest-cov
```

### 全テストの実行

```bash
# プロジェクトルートから実行
cd /path/to/plc-dashboard/raspi_agent
pytest
```

### 特定のテストファイルのみ実行

```bash
pytest tests/test_plc_drivers_base.py
```

### 詳細な出力で実行

```bash
pytest -v
```

### カバレッジレポート付きで実行

```bash
pytest --cov=plc_drivers --cov-report=html
```

### マーカーを使用したフィルタリング

```bash
# ユニットテストのみ実行
pytest -m unit

# 統合テストのみ実行
pytest -m integration

# PLC接続が不要なテストのみ実行
pytest -m "not requires_plc"
```

## テストマーカー

- `@pytest.mark.unit` - ユニットテスト（外部依存なし、高速）
- `@pytest.mark.integration` - 統合テスト（外部システムとの連携）
- `@pytest.mark.slow` - 実行時間が長いテスト
- `@pytest.mark.requires_plc` - 実際のPLC接続が必要なテスト

## テスト作成ガイドライン

### 1. ユニットテスト

- 外部依存を持たない
- 高速に実行できる
- 1つの関数/メソッドをテスト
- モックを活用

```python
@pytest.mark.unit
def test_extract_address_number():
    assert extract_address_number("D100") == 100
```

### 2. 統合テスト

- 複数のモジュールの連携をテスト
- 実際のDB接続やPLC接続が必要な場合あり
- テスト環境を適切にセットアップ

```python
@pytest.mark.integration
def test_plc_connection():
    plc = connect_mitsubishi_plc("192.168.0.10", 5007)
    assert plc is not None
```

### 3. テストの命名規則

- テストファイル: `test_*.py`
- テストクラス: `Test*`
- テスト関数: `test_*`

### 4. アサーション

- 明確なアサーションメッセージを記述
- 期待値と実際の値を比較

```python
def test_dummy_data_generation():
    data = generate_dummy_data({"temp": {"enabled": True, "data_type": "word"}})
    assert "temp" in data, "ダミーデータに'temp'キーが存在すること"
    assert isinstance(data["temp"], (int, float)), "値は数値型であること"
```

## CI/CD統合

GitHub Actionsでテストを自動実行する場合の設定例：

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=plc_drivers
```

## トラブルシューティング

### ModuleNotFoundError

```bash
# PYTHONPATHを設定
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Import Error: plc_drivers

プロジェクトルート（`raspi_agent`）から実行してください：

```bash
cd /path/to/plc-dashboard/raspi_agent
pytest tests/
```

## 今後の拡張予定

- [ ] plc_drivers.mitsubishiのテスト
- [ ] plc_drivers.omronのテスト
- [ ] plc_drivers.keyenceのテスト
- [ ] plc_drivers.siemensのテスト
- [ ] db_utilsモジュールのテスト
- [ ] エンドツーエンドテスト
