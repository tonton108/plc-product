# models.py (更新版)
from db import db
from datetime import datetime

class Equipment(db.Model):
    __tablename__ = 'equipments'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50), unique=True, nullable=False)
    manufacturer = db.Column(db.String(50))
    series = db.Column(db.String(50))
    ip = db.Column(db.String(100))        # ラズパイのIPアドレス
    plc_ip = db.Column(db.String(100))    # PLCのIPアドレス
    mac_address = db.Column(db.String(50))  # ラズパイのMACアドレス
    cpu_serial_number = db.Column(db.String(50), unique=True)  # ラズパイのCPUシリアル番号（不変識別子）
    hostname = db.Column(db.String(100))    # ラズパイのホスト名
    port = db.Column(db.Integer)             # PLCのポート
    modbus_port = db.Column(db.Integer, default=502)  # キーエンス用Modbusポート
    interval = db.Column(db.Integer)

    # ステータスを2つのフィールドに分離（セットアップ状態と運用状態）
    setup_status = db.Column(db.String(50), nullable=False, default="未登録")
    operational_status = db.Column(db.String(50), nullable=False, default="未稼働")

    # PLC通信設定（Phase 1）
    protocol = db.Column(db.String(20), nullable=False, default='MC_PROTOCOL_3E')
    communication_mode = db.Column(db.String(20), nullable=False, default='TCP')
    timeout = db.Column(db.Integer, nullable=False, default=5000)  # ミリ秒
    retry_count = db.Column(db.Integer, nullable=False, default=3)
    retry_interval = db.Column(db.Integer, nullable=False, default=1000)  # ミリ秒

    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # リレーション
    plc_configs = db.relationship('PLCDataConfig', backref='equipment', lazy=True, cascade='all, delete-orphan')

    def __init__(self, equipment_id, manufacturer="", series="", ip="", plc_ip="", mac_address="", cpu_serial_number="", hostname="", port=0, modbus_port=502, interval=60, setup_status="未登録", operational_status="未稼働", protocol="MC_PROTOCOL_3E", communication_mode="TCP", timeout=5000, retry_count=3, retry_interval=1000):
        self.equipment_id = equipment_id
        self.manufacturer = manufacturer
        self.series = series
        self.ip = ip              # ラズパイのIPアドレス
        self.plc_ip = plc_ip      # PLCのIPアドレス
        self.mac_address = mac_address
        self.cpu_serial_number = cpu_serial_number  # CPUシリアル番号
        self.hostname = hostname
        self.port = port
        self.modbus_port = modbus_port
        self.interval = interval
        self.setup_status = setup_status
        self.operational_status = operational_status
        self.protocol = protocol
        self.communication_mode = communication_mode
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_interval = retry_interval

class PLCDataConfig(db.Model):
    """PLCデータ項目設定テーブル（動的項目対応）"""
    __tablename__ = 'plc_data_configs'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'), nullable=False)

    # ユーザー定義項目フィールド（新規追加）
    name = db.Column(db.String(100), nullable=False)      # 項目名（例: "金型温度A"）
    icon = db.Column(db.String(10), default='')           # アイコン（絵文字、例: "🌡️"）
    unit = db.Column(db.String(20), default='')           # 単位（例: "℃", "A", "個"）

    # PLC設定フィールド
    data_type = db.Column(db.String(50), nullable=False)  # 内部キー（後方互換性のため残す）
    enabled = db.Column(db.Boolean, default=True)
    address = db.Column(db.String(20), nullable=False)    # D100, D101など
    scale_factor = db.Column(db.Integer, default=1)       # 倍率
    plc_data_type = db.Column(db.String(20), default='word')  # bit, word, dword, float32

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, equipment_id, data_type, name="", enabled=True, address="", scale_factor=1, plc_data_type="word", icon="", unit=""):
        self.equipment_id = equipment_id
        self.data_type = data_type  # 内部キー（後方互換性）
        self.name = name if name else data_type  # 項目名が空なら内部キーを使用
        self.icon = icon
        self.unit = unit
        self.enabled = enabled
        self.address = address
        self.scale_factor = scale_factor
        self.plc_data_type = plc_data_type

class Log(db.Model):
    """ログテーブル（全データ項目対応版 + 動的JSON対応）"""
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'))

    # 既存項目（後方互換性のため保持）
    current = db.Column(db.Float)
    temperature = db.Column(db.Float)
    pressure = db.Column(db.Float)

    # 新規追加項目（後方互換性のため保持）
    production_count = db.Column(db.Integer)      # 生産数量
    cycle_time = db.Column(db.Float)              # サイクルタイム
    error_code = db.Column(db.Integer)            # エラーコード

    #  動的データ対応JSON型カラム（新規追加）
    # 例: {"temp_a": 25.5, "pressure_b": 100.2, "custom_sensor": 42}
    data = db.Column(db.JSON, nullable=True)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class DailyLogSummary(db.Model):
    """日次集計ログテーブル + 動的JSON対応"""
    __tablename__ = 'daily_log_summaries'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

    # 統計データ（後方互換性のため保持）
    production_count_total = db.Column(db.Integer)      # 1日の総生産数
    current_avg = db.Column(db.Float)                   # 平均電流
    current_max = db.Column(db.Float)                   # 最大電流
    current_min = db.Column(db.Float)                   # 最小電流
    temperature_avg = db.Column(db.Float)               # 平均温度
    temperature_max = db.Column(db.Float)               # 最大温度
    temperature_min = db.Column(db.Float)               # 最小温度
    pressure_avg = db.Column(db.Float)                  # 平均圧力
    pressure_max = db.Column(db.Float)                  # 最大圧力
    pressure_min = db.Column(db.Float)                  # 最小圧力
    cycle_time_avg = db.Column(db.Float)                # 平均サイクルタイム
    error_count = db.Column(db.Integer)                 # エラー発生回数
    data_count = db.Column(db.Integer)                  # 元データ件数

    #  動的データ対応JSON型カラム（新規追加）
    # 例: {"temp_a_avg": 25.5, "temp_a_max": 30.0, "pressure_b_avg": 100.2}
    data_summary = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ユニーク制約
    __table_args__ = (db.UniqueConstraint('equipment_id', 'date', name='uq_equipment_date'),)
    
    def __init__(self, equipment_id, date, production_count_total=None, current_avg=None, current_max=None, current_min=None,
                 temperature_avg=None, temperature_max=None, temperature_min=None, pressure_avg=None, pressure_max=None,
                 pressure_min=None, cycle_time_avg=None, error_count=None, data_count=None):
        self.equipment_id = equipment_id
        self.date = date
        self.production_count_total = production_count_total
        self.current_avg = current_avg
        self.current_max = current_max
        self.current_min = current_min
        self.temperature_avg = temperature_avg
        self.temperature_max = temperature_max
        self.temperature_min = temperature_min
        self.pressure_avg = pressure_avg
        self.pressure_max = pressure_max
        self.pressure_min = pressure_min
        self.cycle_time_avg = cycle_time_avg
        self.error_count = error_count
        self.data_count = data_count

class MonthlyLogSummary(db.Model):
    """月次集計ログテーブル + 動的JSON対応"""
    __tablename__ = 'monthly_log_summaries'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)

    # 統計データ（日次集計の集約、後方互換性のため保持）
    production_count_total = db.Column(db.Integer)
    current_avg = db.Column(db.Float)
    current_max = db.Column(db.Float)
    current_min = db.Column(db.Float)
    temperature_avg = db.Column(db.Float)
    temperature_max = db.Column(db.Float)
    temperature_min = db.Column(db.Float)
    pressure_avg = db.Column(db.Float)
    # 注: pressure_max, pressure_minはDBスキーマに存在しないため、コメントアウト
    # pressure_max = db.Column(db.Float)
    # pressure_min = db.Column(db.Float)
    cycle_time_avg = db.Column(db.Float)
    error_count_total = db.Column(db.Integer)
    operational_days = db.Column(db.Integer)            # 稼働日数

    #  動的データ対応JSON型カラム（新規追加）
    # 例: {"temp_a_avg": 25.5, "temp_a_max": 30.0, "pressure_b_avg": 100.2}
    data_summary = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ユニーク制約
    __table_args__ = (db.UniqueConstraint('equipment_id', 'year', 'month', name='uq_equipment_year_month'),)
    
    def __init__(self, equipment_id, year, month, production_count_total=None, current_avg=None, current_max=None,
                 current_min=None, temperature_avg=None, temperature_max=None, temperature_min=None, pressure_avg=None,
                 cycle_time_avg=None, error_count_total=None, operational_days=None):
        self.equipment_id = equipment_id
        self.year = year
        self.month = month
        self.production_count_total = production_count_total
        self.current_avg = current_avg
        self.current_max = current_max
        self.current_min = current_min
        self.temperature_avg = temperature_avg
        self.temperature_max = temperature_max
        self.temperature_min = temperature_min
        self.pressure_avg = pressure_avg
        # pressure_max, pressure_minは削除
        self.cycle_time_avg = cycle_time_avg
        self.error_count_total = error_count_total
        self.operational_days = operational_days

# ステータス定数（セットアップ状態）
class SetupStatus:
    NOT_REGISTERED = "未登録"                  # 設備未登録
    BASIC_INFO_REGISTERED = "基本情報登録済み"  # 基本情報のみ登録
    PLC_CONFIGURED = "PLC設定済み"             # PLC設定完了
    SETUP_COMPLETE = "セットアップ完了"        # 初回データ受信完了

    @classmethod
    def get_all(cls):
        return [
            cls.NOT_REGISTERED,
            cls.BASIC_INFO_REGISTERED,
            cls.PLC_CONFIGURED,
            cls.SETUP_COMPLETE
        ]

    @classmethod
    def get_display_names(cls):
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
    def get_all(cls):
        return [
            cls.NOT_STARTED,
            cls.RUNNING,
            cls.WARNING,
            cls.ERROR,
            cls.STOPPED,
            cls.MAINTENANCE
        ]

    @classmethod
    def get_display_names(cls):
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
    def get_all(cls):
        return [
            cls.PRODUCTION_COUNT,
            cls.CURRENT,
            cls.TEMPERATURE,
            cls.PRESSURE,
            cls.CYCLE_TIME,
            cls.ERROR_CODE
        ]

    @classmethod
    def get_display_names(cls):
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
    def get_all(cls):
        return [cls.BIT, cls.WORD, cls.DWORD, cls.FLOAT32]

    @classmethod
    def get_display_names(cls):
        return {
            cls.BIT: "Bit",
            cls.WORD: "Word (16bit)",
            cls.DWORD: "DWord (32bit)",
            cls.FLOAT32: "Float32"
        }

# PLCプロトコル定数（Phase 1追加）
class PLCProtocols:
    MC_PROTOCOL_3E = "MC_PROTOCOL_3E"       # 三菱PLCプロトコル（QnA互換3Eフレーム）
    MC_PROTOCOL_4E = "MC_PROTOCOL_4E"       # 三菱PLCプロトコル（QnA互換4Eフレーム）
    FINS = "FINS"                           # オムロンPLCプロトコル
    MODBUS = "MODBUS"                       # Modbusプロトコル（キーエンス等）

    @classmethod
    def get_all(cls):
        return [cls.MC_PROTOCOL_3E, cls.MC_PROTOCOL_4E, cls.FINS, cls.MODBUS]

    @classmethod
    def get_display_names(cls):
        return {
            cls.MC_PROTOCOL_3E: "MC Protocol 3E（三菱 QnA互換）",
            cls.MC_PROTOCOL_4E: "MC Protocol 4E（三菱 QnA互換）",
            cls.FINS: "FINS（オムロン）",
            cls.MODBUS: "Modbus TCP（キーエンス等）"
        }

    @classmethod
    def get_manufacturer_default(cls, manufacturer):
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

# 通信モード定数（Phase 1追加）
class CommunicationModes:
    TCP = "TCP"
    UDP = "UDP"

    @classmethod
    def get_all(cls):
        return [cls.TCP, cls.UDP]

    @classmethod
    def get_display_names(cls):
        return {
            cls.TCP: "TCP（信頼性重視）",
            cls.UDP: "UDP（速度重視）"
        }

    @classmethod
    def get_protocol_default(cls, protocol):
        """プロトコルに応じたデフォルト通信モードを返す"""
        # ほとんどのPLCプロトコルはTCPを使用
        # UDPを使うケースは限定的（高速リアルタイム通信など）
        return cls.TCP

# Phase 2: エラーログ・アラーム履歴・PLC状態テーブル

class CommunicationErrorLog(db.Model):
    """PLC通信エラーログテーブル"""
    __tablename__ = 'communication_error_logs'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'), nullable=False)
    error_type = db.Column(db.String(50), nullable=False)  # TIMEOUT, CONNECTION_FAILED等
    error_code = db.Column(db.String(20))
    error_message = db.Column(db.Text())
    retry_count = db.Column(db.Integer())
    plc_ip = db.Column(db.String(100))
    protocol = db.Column(db.String(20))
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime())
    resolution_method = db.Column(db.String(50))

    def __init__(self, equipment_id, error_type, error_message="", occurred_at=None,
                 error_code="", retry_count=0, plc_ip="", protocol=""):
        self.equipment_id = equipment_id
        self.error_type = error_type
        self.error_code = error_code
        self.error_message = error_message
        self.retry_count = retry_count
        self.plc_ip = plc_ip
        self.protocol = protocol
        self.occurred_at = occurred_at or datetime.utcnow()


class AlarmHistory(db.Model):
    """PLCアラーム履歴テーブル"""
    __tablename__ = 'alarm_history'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'), nullable=False)
    alarm_code = db.Column(db.String(20), nullable=False)
    alarm_level = db.Column(db.String(20), nullable=False)  # WARNING, ERROR, CRITICAL
    alarm_message = db.Column(db.Text())
    alarm_data = db.Column(db.JSON)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cleared_at = db.Column(db.DateTime())
    acknowledged = db.Column(db.Boolean, default=False, nullable=False)
    acknowledged_by = db.Column(db.String(50))
    acknowledged_at = db.Column(db.DateTime())

    def __init__(self, equipment_id, alarm_code, alarm_level, alarm_message="",
                 alarm_data=None, occurred_at=None):
        self.equipment_id = equipment_id
        self.alarm_code = alarm_code
        self.alarm_level = alarm_level
        self.alarm_message = alarm_message
        self.alarm_data = alarm_data
        self.occurred_at = occurred_at or datetime.utcnow()


class PLCStatus(db.Model):
    """PLC通信状態のリアルタイム監視テーブル"""
    __tablename__ = 'plc_status'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'), nullable=False, unique=True)
    last_communication_at = db.Column(db.DateTime())
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    consecutive_errors = db.Column(db.Integer, default=0, nullable=False)
    last_error_type = db.Column(db.String(50))
    last_error_message = db.Column(db.Text())
    uptime_seconds = db.Column(db.Integer, default=0, nullable=False)
    last_status_change_at = db.Column(db.DateTime())

    def __init__(self, equipment_id):
        self.equipment_id = equipment_id
        self.is_online = False
        self.consecutive_errors = 0
        self.uptime_seconds = 0


# エラー種別定数
class ErrorTypes:
    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def get_all(cls):
        return [
            cls.TIMEOUT,
            cls.CONNECTION_FAILED,
            cls.PROTOCOL_ERROR,
            cls.AUTHENTICATION_FAILED,
            cls.DATA_VALIDATION_ERROR,
            cls.UNKNOWN
        ]

    @classmethod
    def get_display_names(cls):
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
    def get_all(cls):
        return [cls.WARNING, cls.ERROR, cls.CRITICAL]

    @classmethod
    def get_display_names(cls):
        return {
            cls.WARNING: "警告",
            cls.ERROR: "エラー",
            cls.CRITICAL: "致命的"
        }


# デフォルト設定を作成するヘルパー関数
def create_default_plc_configs(equipment_id):
    """設備登録時に呼び出してデフォルトのPLC設定を作成"""
    default_configs = [
        {"data_type": DataTypes.PRODUCTION_COUNT, "enabled": False, "address": "D150", "scale_factor": 1, "plc_data_type": "word"},
        {"data_type": DataTypes.CURRENT, "enabled": True, "address": "D100", "scale_factor": 10, "plc_data_type": "word"},
        {"data_type": DataTypes.TEMPERATURE, "enabled": True, "address": "D101", "scale_factor": 10, "plc_data_type": "float32"},
        {"data_type": DataTypes.PRESSURE, "enabled": True, "address": "D102", "scale_factor": 100, "plc_data_type": "word"},
        {"data_type": DataTypes.CYCLE_TIME, "enabled": False, "address": "D200", "scale_factor": 1, "plc_data_type": "dword"},
        {"data_type": DataTypes.ERROR_CODE, "enabled": False, "address": "D300", "scale_factor": 1, "plc_data_type": "word"},
    ]
    
    for config in default_configs:
        plc_config = PLCDataConfig(
            equipment_id=equipment_id,
            data_type=config["data_type"],
            enabled=config["enabled"],
            address=config["address"],
            scale_factor=config["scale_factor"],
            plc_data_type=config["plc_data_type"]
        )
        db.session.add(plc_config)
    
    db.session.commit() 