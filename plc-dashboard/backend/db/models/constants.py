"""
定数クラスモジュール

ステータス、データ型、プロトコルなどの定数を定義します。

Phase 17: models.pyから分割
"""

from typing import List, Dict


# ステータス定数（セットアップ状態）
class SetupStatus:
    NOT_REGISTERED = "未登録"                  # 設備未登録
    BASIC_INFO_REGISTERED = "基本情報登録済み"  # 基本情報のみ登録
    PLC_CONFIGURED = "PLC設定済み"             # PLC設定完了
    SETUP_COMPLETE = "セットアップ完了"        # 初回データ受信完了

    @classmethod
    def get_all(cls) -> List[str]:
        return [
            cls.NOT_REGISTERED,
            cls.BASIC_INFO_REGISTERED,
            cls.PLC_CONFIGURED,
            cls.SETUP_COMPLETE
        ]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.NOT_REGISTERED: "未登録",
            cls.BASIC_INFO_REGISTERED: "基本情報登録済み",
            cls.PLC_CONFIGURED: "PLC設定済み",
            cls.SETUP_COMPLETE: "セットアップ完了"
        }


# ステータス定数（運用状態）
class OperationalStatus:
    NOT_STARTED = "未稼働"       # 初回データ受信前
    RUNNING = "稼働中"           # データ受信中（正常）
    WARNING = "警告"             # データに異常値
    ERROR = "エラー"             # 通信エラーなど
    STOPPED = "停止中"           # 長期間データなし
    MAINTENANCE = "メンテナンス中"  # 手動で停止

    @classmethod
    def get_all(cls) -> List[str]:
        return [
            cls.NOT_STARTED,
            cls.RUNNING,
            cls.WARNING,
            cls.ERROR,
            cls.STOPPED,
            cls.MAINTENANCE
        ]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.NOT_STARTED: "未稼働",
            cls.RUNNING: "稼働中",
            cls.WARNING: "警告",
            cls.ERROR: "エラー",
            cls.STOPPED: "停止中",
            cls.MAINTENANCE: "メンテナンス中"
        }


# データ型定数
class DataTypes:
    PRODUCTION_COUNT = "production_count"
    CURRENT = "current"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    CYCLE_TIME = "cycle_time"
    ERROR_CODE = "error_code"

    @classmethod
    def get_all(cls) -> List[str]:
        return [
            cls.PRODUCTION_COUNT,
            cls.CURRENT,
            cls.TEMPERATURE,
            cls.PRESSURE,
            cls.CYCLE_TIME,
            cls.ERROR_CODE
        ]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.PRODUCTION_COUNT: "生産数量",
            cls.CURRENT: "電流",
            cls.TEMPERATURE: "温度",
            cls.PRESSURE: "圧力",
            cls.CYCLE_TIME: "サイクルタイム",
            cls.ERROR_CODE: "エラーコード"
        }


# PLCデータ型定数
class PLCDataTypes:
    BIT = "bit"
    WORD = "word"
    DWORD = "dword"
    FLOAT32 = "float32"

    @classmethod
    def get_all(cls) -> List[str]:
        return [cls.BIT, cls.WORD, cls.DWORD, cls.FLOAT32]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.BIT: "Bit",
            cls.WORD: "Word (16bit)",
            cls.DWORD: "DWord (32bit)",
            cls.FLOAT32: "Float32"
        }


# PLCプロトコル定数
class PLCProtocols:
    MC_PROTOCOL_3E = "MC_PROTOCOL_3E"       # 三菱PLCプロトコル（QnA互換3Eフレーム）
    MC_PROTOCOL_4E = "MC_PROTOCOL_4E"       # 三菱PLCプロトコル（QnA互換4Eフレーム）
    FINS = "FINS"                           # オムロンPLCプロトコル
    MODBUS = "MODBUS"                       # Modbusプロトコル（キーエンス等）

    @classmethod
    def get_all(cls) -> List[str]:
        return [cls.MC_PROTOCOL_3E, cls.MC_PROTOCOL_4E, cls.FINS, cls.MODBUS]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.MC_PROTOCOL_3E: "MC Protocol 3E（三菱 QnA互換）",
            cls.MC_PROTOCOL_4E: "MC Protocol 4E（三菱 QnA互換）",
            cls.FINS: "FINS（オムロン）",
            cls.MODBUS: "Modbus TCP（キーエンス等）"
        }

    @classmethod
    def get_manufacturer_default(cls, manufacturer: str) -> str:
        """メーカー名からデフォルトプロトコルを推定"""
        if not manufacturer:
            return cls.MC_PROTOCOL_3E

        manufacturer_lower = manufacturer.lower()

        if '三菱' in manufacturer or 'mitsubishi' in manufacturer_lower:
            return cls.MC_PROTOCOL_3E
        elif 'オムロン' in manufacturer or 'omron' in manufacturer_lower:
            return cls.FINS
        elif 'キーエンス' in manufacturer or 'keyence' in manufacturer_lower:
            return cls.MODBUS
        else:
            return cls.MC_PROTOCOL_3E  # デフォルト


# 通信モード定数
class CommunicationModes:
    TCP = "TCP"
    UDP = "UDP"

    @classmethod
    def get_all(cls) -> List[str]:
        return [cls.TCP, cls.UDP]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.TCP: "TCP（信頼性重視）",
            cls.UDP: "UDP（速度重視）"
        }

    @classmethod
    def get_protocol_default(cls, protocol: str) -> str:
        """プロトコルに応じたデフォルト通信モードを返す"""
        # ほとんどのPLCプロトコルはTCPを使用
        # UDPを使うケースは限定的（高速リアルタイム通信など）
        return cls.TCP


# エラー種別定数
class ErrorTypes:
    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def get_all(cls) -> List[str]:
        return [
            cls.TIMEOUT,
            cls.CONNECTION_FAILED,
            cls.PROTOCOL_ERROR,
            cls.AUTHENTICATION_FAILED,
            cls.DATA_VALIDATION_ERROR,
            cls.UNKNOWN
        ]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.TIMEOUT: "タイムアウト",
            cls.CONNECTION_FAILED: "接続失敗",
            cls.PROTOCOL_ERROR: "プロトコルエラー",
            cls.AUTHENTICATION_FAILED: "認証失敗",
            cls.DATA_VALIDATION_ERROR: "データ検証エラー",
            cls.UNKNOWN: "不明なエラー"
        }


# アラームレベル定数
class AlarmLevels:
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def get_all(cls) -> List[str]:
        return [cls.WARNING, cls.ERROR, cls.CRITICAL]

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        return {
            cls.WARNING: "警告",
            cls.ERROR: "エラー",
            cls.CRITICAL: "致命的"
        }
