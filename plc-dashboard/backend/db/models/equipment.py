"""
設備モデルモジュール

Equipment（設備）とPLCDataConfig（PLCデータ設定）を定義します。

Phase 17: models.pyから分割
"""

from datetime import datetime, timezone
from db import db


class Equipment(db.Model):
    """設備テーブル"""
    __tablename__ = 'equipments'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50), unique=True, nullable=False)
    # nullable=False はマイグレーション d1e2f3g4h5i6 でDBに適用済みのNOT NULL制約と対応
    manufacturer = db.Column(db.String(50), nullable=False)
    series = db.Column(db.String(50), nullable=False)
    ip = db.Column(db.String(100))        # ラズパイのIPアドレス
    plc_ip = db.Column(db.String(100), nullable=False)    # PLCのIPアドレス
    mac_address = db.Column(db.String(50))  # ラズパイのMACアドレス
    cpu_serial_number = db.Column(db.String(50), unique=True, nullable=False)  # ラズパイのCPUシリアル番号（不変識別子）
    hostname = db.Column(db.String(100))    # ラズパイのホスト名
    port = db.Column(db.Integer, nullable=False)             # PLCのポート
    modbus_port = db.Column(db.Integer, default=502)  # キーエンス用Modbusポート
    interval = db.Column(db.Integer, nullable=False)

    # ステータスを2つのフィールドに分離（セットアップ状態と運用状態）
    setup_status = db.Column(db.String(50), nullable=False, default="未登録")
    operational_status = db.Column(db.String(50), nullable=False, default="未稼働")

    # PLC通信設定（Phase 1）
    protocol = db.Column(db.String(20), nullable=False, default='MC_PROTOCOL_3E')
    communication_mode = db.Column(db.String(20), nullable=False, default='TCP')
    timeout = db.Column(db.Integer, nullable=False, default=5000)  # ミリ秒
    retry_count = db.Column(db.Integer, nullable=False, default=3)
    retry_interval = db.Column(db.Integer, nullable=False, default=1000)  # ミリ秒

    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # リレーション
    plc_configs = db.relationship('PLCDataConfig', backref='equipment', lazy=True, cascade='all, delete-orphan')

    def __init__(
        self,
        equipment_id: str,
        manufacturer: str = "",
        series: str = "",
        ip: str = "",
        plc_ip: str = "",
        mac_address: str = "",
        cpu_serial_number: str = "",
        hostname: str = "",
        port: int = 0,
        modbus_port: int = 502,
        interval: int = 60,
        setup_status: str = "未登録",
        operational_status: str = "未稼働",
        protocol: str = "MC_PROTOCOL_3E",
        communication_mode: str = "TCP",
        timeout: int = 5000,
        retry_count: int = 3,
        retry_interval: int = 1000
    ):
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
    scale_factor = db.Column(db.Float, default=1)          # 倍率
    plc_data_type = db.Column(db.String(20), default='word')  # bit, word, dword, float32
    # 32bit値（dword/float32）のワード間順序（Phase 2）
    # high_first: 先頭アドレス=上位（シーメンス等）/ low_first: 先頭アドレス=下位（三菱等）
    # 既定は low_first（三菱MELSECが最多想定。詳細は _docs/plc-knowledge/endianness.md）
    word_order = db.Column(db.String(20), default='low_first')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        equipment_id: int,
        data_type: str,
        name: str = "",
        enabled: bool = True,
        address: str = "",
        scale_factor: float = 1,
        plc_data_type: str = "word",
        icon: str = "",
        unit: str = "",
        word_order: str = "low_first"
    ):
        self.equipment_id = equipment_id
        self.data_type = data_type  # 内部キー（後方互換性）
        self.name = name if name else data_type  # 項目名が空なら内部キーを使用
        self.icon = icon
        self.unit = unit
        self.enabled = enabled
        self.address = address
        self.scale_factor = scale_factor
        self.plc_data_type = plc_data_type
        self.word_order = word_order
