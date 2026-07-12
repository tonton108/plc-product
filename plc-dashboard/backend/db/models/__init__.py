"""
モデルパッケージ

このパッケージは後方互換性を維持しながら、
論理的に分割されたモデルモジュールを提供します。

Phase 17: models.pyを分割

使用例（後方互換性あり）:
    from db.models import Equipment, Log, SetupStatus
    from db.models import create_default_plc_configs

新しい推奨インポート方法:
    from db.models.equipment import Equipment, PLCDataConfig
    from db.models.logs import Log, DailyLogSummary, MonthlyLogSummary
    from db.models.errors import CommunicationErrorLog, AlarmHistory, PLCStatus
    from db.models.constants import SetupStatus, OperationalStatus
"""

# 設備モデル
from .equipment import Equipment, PLCDataConfig

# ログモデル
from .logs import Log, DailyLogSummary, MonthlyLogSummary

# エラー・アラームモデル
from .errors import CommunicationErrorLog, AlarmHistory, PLCStatus, IncidentContext

# 認証モデル（Phase 1）
from .auth import User, AuthToken, AgentApiKey, UserRoles

# 定数クラス
from .constants import (
    SetupStatus,
    OperationalStatus,
    DataTypes,
    PLCDataTypes,
    PLCProtocols,
    CommunicationModes,
    ErrorTypes,
    AlarmLevels,
)

# ヘルパー関数
from .helpers import create_default_plc_configs

# 後方互換性のための__all__定義
__all__ = [
    # 設備モデル
    'Equipment',
    'PLCDataConfig',
    # ログモデル
    'Log',
    'DailyLogSummary',
    'MonthlyLogSummary',
    # エラー・アラームモデル
    'CommunicationErrorLog',
    'AlarmHistory',
    'PLCStatus',
    'IncidentContext',
    # 認証モデル（Phase 1）
    'User',
    'AuthToken',
    'AgentApiKey',
    'UserRoles',
    # 定数クラス
    'SetupStatus',
    'OperationalStatus',
    'DataTypes',
    'PLCDataTypes',
    'PLCProtocols',
    'CommunicationModes',
    'ErrorTypes',
    'AlarmLevels',
    # ヘルパー関数
    'create_default_plc_configs',
]
