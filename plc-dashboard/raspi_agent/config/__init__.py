"""
設定モジュール

Phase 7リファクタリング: agent_app.pyからの分割
Phase 9追加: constants.py（定数定義）

このパッケージは以下を提供します:
- app_config: Flask/Babel/SocketIO初期化
- plc_config: PLCメーカー・シリーズ定義
- constants: タイムアウト、デフォルト値などの定数
"""

from .app_config import init_app_config, get_locale
from .plc_config import MANUFACTURERS, SERIES_LIST
from .constants import (
    API_TIMEOUT,
    LONG_OPERATION_TIMEOUT,
    THREAD_JOIN_TIMEOUT,
    DEFAULT_CENTRAL_SERVER_IP,
    DEFAULT_CENTRAL_SERVER_PORT,
    DEFAULT_PLC_IP,
    DEFAULT_PLC_PORT,
    DEFAULT_MODBUS_PORT,
    MAX_RETRY_COUNT,
    BUFFER_CLEANUP_DAYS,
    BUFFER_BATCH_SIZE,
    DEFAULT_INTERVAL_MS,
    SESSION_LIFETIME_SECONDS,
    COOKIE_MAX_AGE_SECONDS,
)

__all__ = [
    'init_app_config',
    'get_locale',
    'MANUFACTURERS',
    'SERIES_LIST',
    # 定数
    'API_TIMEOUT',
    'LONG_OPERATION_TIMEOUT',
    'THREAD_JOIN_TIMEOUT',
    'DEFAULT_CENTRAL_SERVER_IP',
    'DEFAULT_CENTRAL_SERVER_PORT',
    'DEFAULT_PLC_IP',
    'DEFAULT_PLC_PORT',
    'DEFAULT_MODBUS_PORT',
    'MAX_RETRY_COUNT',
    'BUFFER_CLEANUP_DAYS',
    'BUFFER_BATCH_SIZE',
    'DEFAULT_INTERVAL_MS',
    'SESSION_LIFETIME_SECONDS',
    'COOKIE_MAX_AGE_SECONDS',
]
