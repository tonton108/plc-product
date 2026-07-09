"""
バックエンドAPI定数定義

Phase 12: ハードコード値の定数化
Phase 15: DB設定・バッチ処理定数追加
"""

# ネットワーク設定
DEFAULT_MODBUS_PORT = 502

# タイムアウト設定（ミリ秒）
DEFAULT_TIMEOUT_MS = 5000
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_INTERVAL_MS = 1000

# データ収集間隔（ミリ秒）
DEFAULT_INTERVAL_MS = 5000

# データベース接続設定（Phase 15）
DEFAULT_DB_URL = "postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor"
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 50
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 300
DB_HEALTH_CHECK_SQL = "SELECT 1"

# バッチ処理設定（Phase 15）
BATCH_DELETE_SIZE = 1000
DEFAULT_CLEANUP_DAYS = 30
