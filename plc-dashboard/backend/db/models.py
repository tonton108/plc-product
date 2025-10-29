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
    plc_ip = db.Column(db.String(100))    # PLCのIPアドレス（新規追加）
    mac_address = db.Column(db.String(50))  # ラズパイのMACアドレス
    cpu_serial_number = db.Column(db.String(50), unique=True)  # ラズパイのCPUシリアル番号（不変識別子）
    hostname = db.Column(db.String(100))    # ラズパイのホスト名
    port = db.Column(db.Integer)             # PLCのポート
    modbus_port = db.Column(db.Integer, default=502)  # キーエンス用Modbusポート
    interval = db.Column(db.Integer)
    status = db.Column(db.String(50), default="正常")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーション
    plc_configs = db.relationship('PLCDataConfig', backref='equipment', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, equipment_id, manufacturer="", series="", ip="", plc_ip="", mac_address="", cpu_serial_number="", hostname="", port=0, modbus_port=502, interval=60, status="正常"):
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
        self.status = status

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
    pressure_max = db.Column(db.Float)
    pressure_min = db.Column(db.Float)
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
                 pressure_max=None, pressure_min=None, cycle_time_avg=None, error_count_total=None, operational_days=None):
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
        self.pressure_max = pressure_max
        self.pressure_min = pressure_min
        self.cycle_time_avg = cycle_time_avg
        self.error_count_total = error_count_total
        self.operational_days = operational_days

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