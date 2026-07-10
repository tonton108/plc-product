"""
ログモデルモジュール

Log（ログ）、DailyLogSummary（日次集計）、MonthlyLogSummary（月次集計）を定義します。

Phase 17: models.pyから分割
"""

from datetime import datetime, timezone
from typing import Optional
from db import db


# ログの固定カラム（後方互換）に対応するキー。これら以外の受信項目は
# 動的項目として Log.data(JSON) に格納する（Phase 2: 動的データ項目の一気通貫）
FIXED_LOG_FIELDS = (
    "production_count",
    "current",
    "temperature",
    "pressure",
    "cycle_time",
    "error_code",
)

# 受信JSONのうち、データ項目ではないメタキー（data に混ぜない）
LOG_META_FIELDS = ("equipment_id", "timestamp")


class Log(db.Model):
    """ログテーブル（全データ項目対応版 + 動的JSON対応）

    Phase 3: Postgresでは timestamp による月次RANGEパーティションを採用（実PKは
    (id, timestamp)）。ただしSQLiteは複合PKのオートインクリメントを非対応のため、
    モデル上のPKは id 単独のまま維持し、複合PK・パーティション化はPostgres側の
    マイグレーションでのみ適用する（単体テストはSQLiteの非パーティションtableで実行）。
    timestamp はパーティションキーのため NOT NULL（既定値で自動補完）。
    """
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

    # パーティションキー。NOT NULL（未指定時は既定値で補完）。
    timestamp = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


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

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ユニーク制約
    __table_args__ = (db.UniqueConstraint('equipment_id', 'date', name='uq_equipment_date'),)

    def __init__(
        self,
        equipment_id: int,
        date,
        production_count_total: Optional[int] = None,
        current_avg: Optional[float] = None,
        current_max: Optional[float] = None,
        current_min: Optional[float] = None,
        temperature_avg: Optional[float] = None,
        temperature_max: Optional[float] = None,
        temperature_min: Optional[float] = None,
        pressure_avg: Optional[float] = None,
        pressure_max: Optional[float] = None,
        pressure_min: Optional[float] = None,
        cycle_time_avg: Optional[float] = None,
        error_count: Optional[int] = None,
        data_count: Optional[int] = None,
        data_summary: Optional[dict] = None
    ):
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
        self.data_summary = data_summary


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
    # マイグレーション b2c3d4e5f6a7 でDBに追加済みのカラム（モデル側の欠落を解消）
    pressure_max = db.Column(db.Float)
    pressure_min = db.Column(db.Float)
    cycle_time_avg = db.Column(db.Float)
    error_count_total = db.Column(db.Integer)
    operational_days = db.Column(db.Integer)            # 稼働日数

    #  動的データ対応JSON型カラム（新規追加）
    # 例: {"temp_a_avg": 25.5, "temp_a_max": 30.0, "pressure_b_avg": 100.2}
    data_summary = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ユニーク制約
    __table_args__ = (db.UniqueConstraint('equipment_id', 'year', 'month', name='uq_equipment_year_month'),)

    def __init__(
        self,
        equipment_id: int,
        year: int,
        month: int,
        production_count_total: Optional[int] = None,
        current_avg: Optional[float] = None,
        current_max: Optional[float] = None,
        current_min: Optional[float] = None,
        temperature_avg: Optional[float] = None,
        temperature_max: Optional[float] = None,
        temperature_min: Optional[float] = None,
        pressure_avg: Optional[float] = None,
        pressure_max: Optional[float] = None,
        pressure_min: Optional[float] = None,
        cycle_time_avg: Optional[float] = None,
        error_count_total: Optional[int] = None,
        operational_days: Optional[int] = None,
        data_summary: Optional[dict] = None
    ):
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
        self.data_summary = data_summary
