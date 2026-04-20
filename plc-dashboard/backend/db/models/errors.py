"""
エラー・アラームモデルモジュール

CommunicationErrorLog（通信エラーログ）、AlarmHistory（アラーム履歴）、
PLCStatus（PLC状態）を定義します。

Phase 17: models.pyから分割
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from db import db


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
    occurred_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime())
    resolution_method = db.Column(db.String(50))

    def __init__(
        self,
        equipment_id: int,
        error_type: str,
        error_message: str = "",
        occurred_at: Optional[datetime] = None,
        error_code: str = "",
        retry_count: int = 0,
        plc_ip: str = "",
        protocol: str = ""
    ):
        self.equipment_id = equipment_id
        self.error_type = error_type
        self.error_code = error_code
        self.error_message = error_message
        self.retry_count = retry_count
        self.plc_ip = plc_ip
        self.protocol = protocol
        self.occurred_at = occurred_at or datetime.now(timezone.utc)


class AlarmHistory(db.Model):
    """PLCアラーム履歴テーブル"""
    __tablename__ = 'alarm_history'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'), nullable=False)
    alarm_code = db.Column(db.String(20), nullable=False)
    alarm_level = db.Column(db.String(20), nullable=False)  # WARNING, ERROR, CRITICAL
    alarm_message = db.Column(db.Text())
    alarm_data = db.Column(db.JSON)
    occurred_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    cleared_at = db.Column(db.DateTime())
    acknowledged = db.Column(db.Boolean, default=False, nullable=False)
    acknowledged_by = db.Column(db.String(50))
    acknowledged_at = db.Column(db.DateTime())

    def __init__(
        self,
        equipment_id: int,
        alarm_code: str,
        alarm_level: str,
        alarm_message: str = "",
        alarm_data: Optional[Dict[str, Any]] = None,
        occurred_at: Optional[datetime] = None
    ):
        self.equipment_id = equipment_id
        self.alarm_code = alarm_code
        self.alarm_level = alarm_level
        self.alarm_message = alarm_message
        self.alarm_data = alarm_data
        self.occurred_at = occurred_at or datetime.now(timezone.utc)


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

    def __init__(self, equipment_id: int):
        self.equipment_id = equipment_id
        self.is_online = False
        self.consecutive_errors = 0
        self.uptime_seconds = 0
