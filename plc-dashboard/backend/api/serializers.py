"""
シリアライザーモジュール

このモジュールはデータベースモデルをAPIレスポンス用の辞書に変換する
シリアライザークラスを提供します。

使用例:
    from api.serializers import EquipmentSerializer, LogSerializer

    equipment = Equipment.query.first()
    data = EquipmentSerializer.to_dict(equipment)

    equipments = Equipment.query.all()
    data_list = EquipmentSerializer.to_list(equipments)
"""

from typing import List, Optional, Any
from datetime import datetime
from .constants import DEFAULT_MODBUS_PORT


class EquipmentSerializer:
    """設備（Equipment）モデルのシリアライザー"""

    @staticmethod
    def to_dict(equipment, include_status: bool = True, include_plc_config: bool = True) -> dict:
        """
        Equipmentモデルを辞書に変換

        Args:
            equipment: Equipmentモデルインスタンス
            include_status: ステータス情報を含めるか
            include_plc_config: PLC通信設定を含めるか

        Returns:
            dict: シリアライズされた設備データ
        """
        data = {
            "id": equipment.id,
            "equipment_id": equipment.equipment_id,
            "manufacturer": equipment.manufacturer,
            "series": equipment.series,
            "ip": equipment.ip,
            "plc_ip": getattr(equipment, "plc_ip", ""),
            "port": equipment.port,
            "modbus_port": getattr(equipment, "modbus_port", DEFAULT_MODBUS_PORT),
            # Siemens S7用 Rack/Slot（Issue #58）。エージェントが基底dictから読むため
            # include_plc_config ではなくここに含める（modbus_portと同じ扱い）。
            "rack": getattr(equipment, "rack", 0),
            "slot": getattr(equipment, "slot", 1),
            "interval": equipment.interval,
            "hostname": equipment.hostname,
            "mac_address": equipment.mac_address,
            "cpu_serial_number": getattr(equipment, "cpu_serial_number", ""),
            "updated_at": equipment.updated_at.isoformat() if equipment.updated_at else None
        }

        if include_status:
            data["setup_status"] = equipment.setup_status
            data["operational_status"] = equipment.operational_status
            # 後方互換性のため
            data["status"] = equipment.operational_status

        if include_plc_config:
            data["protocol"] = getattr(equipment, "protocol", "MC_PROTOCOL_3E")
            data["communication_mode"] = getattr(equipment, "communication_mode", "TCP")
            data["timeout"] = getattr(equipment, "timeout", 5000)
            data["retry_count"] = getattr(equipment, "retry_count", 3)
            data["retry_interval"] = getattr(equipment, "retry_interval", 1000)

        return data

    @staticmethod
    def to_list(equipments, **kwargs) -> List[dict]:
        """
        Equipmentモデルのリストを辞書のリストに変換

        Args:
            equipments: Equipmentモデルのリスト
            **kwargs: to_dictに渡すオプション

        Returns:
            List[dict]: シリアライズされた設備データのリスト
        """
        return [EquipmentSerializer.to_dict(eq, **kwargs) for eq in equipments]

    @staticmethod
    def to_search_result(equipment) -> dict:
        """
        検索結果用の軽量シリアライズ

        Args:
            equipment: Equipmentモデルインスタンス

        Returns:
            dict: 検索結果用のデータ
        """
        return {
            "found": True,
            "id": equipment.id,
            "equipment_id": equipment.equipment_id,
            "manufacturer": equipment.manufacturer,
            "series": equipment.series,
            "ip": equipment.ip,
            "port": equipment.port,
            "interval": equipment.interval,
            "setup_status": equipment.setup_status,
            "operational_status": equipment.operational_status,
            "status": equipment.operational_status,  # 後方互換性
            "hostname": equipment.hostname,
            "mac_address": equipment.mac_address,
            "cpu_serial_number": getattr(equipment, "cpu_serial_number", ""),
            "protocol": getattr(equipment, "protocol", "MC_PROTOCOL_3E"),
            "communication_mode": getattr(equipment, "communication_mode", "TCP"),
            "timeout": getattr(equipment, "timeout", 5000),
            "retry_count": getattr(equipment, "retry_count", 3),
            "retry_interval": getattr(equipment, "retry_interval", 1000)
        }


class PLCDataConfigSerializer:
    """PLCデータ設定（PLCDataConfig）モデルのシリアライザー"""

    @staticmethod
    def to_dict(config) -> dict:
        """
        PLCDataConfigモデルを辞書に変換

        Args:
            config: PLCDataConfigモデルインスタンス

        Returns:
            dict: シリアライズされたPLCデータ設定
        """
        return {
            "name": getattr(config, "name", ""),
            "data_type": config.data_type,
            "icon": getattr(config, "icon", ""),
            "enabled": config.enabled,
            "address": config.address,
            "scale_factor": config.scale_factor,
            "plc_data_type": getattr(config, "plc_data_type", "word"),
            "unit": getattr(config, "unit", ""),
            # 32bitワード順序（Phase 2）。エージェントがこの値で変換する
            "word_order": getattr(config, "word_order", "low_first")
        }

    @staticmethod
    def to_list(configs) -> List[dict]:
        """PLCDataConfigモデルのリストを辞書のリストに変換"""
        return [PLCDataConfigSerializer.to_dict(cfg) for cfg in configs]


class LogSerializer:
    """ログ（Log）モデルのシリアライザー"""

    @staticmethod
    def to_dict(log, include_equipment_id: bool = False, equipment_id_str: str = None) -> dict:
        """
        Logモデルを辞書に変換

        Args:
            log: Logモデルインスタンス
            include_equipment_id: equipment_idを含めるか
            equipment_id_str: 設備ID文字列（equipment_idを含める場合）

        Returns:
            dict: シリアライズされたログデータ
        """
        data = {
            "timestamp": log.timestamp.isoformat(),
            "production_count": log.production_count,
            "current": log.current,
            "temperature": log.temperature,
            "pressure": log.pressure,
            "cycle_time": log.cycle_time,
            "error_code": log.error_code
        }

        # 動的項目（Log.data）をフラットにマージ（Phase 2）。
        # 固定カラムと同名キーがあっても固定カラムを優先し、上書きしない
        if log.data:
            for key, value in log.data.items():
                data.setdefault(key, value)

        if include_equipment_id and equipment_id_str:
            data["equipment_id"] = equipment_id_str

        return data

    @staticmethod
    def to_list(logs, **kwargs) -> List[dict]:
        """Logモデルのリストを辞書のリストに変換"""
        return [LogSerializer.to_dict(log, **kwargs) for log in logs]

    @staticmethod
    def to_realtime(log, equipment_id: str) -> dict:
        """
        リアルタイム配信用のシリアライズ

        Args:
            log: Logモデルインスタンス
            equipment_id: 設備ID文字列

        Returns:
            dict: リアルタイム配信用データ
        """
        realtime = {
            "equipment_id": equipment_id,
            "timestamp": log.timestamp.isoformat(),
            "production_count": log.production_count,
            "current": log.current,
            "temperature": log.temperature,
            "pressure": log.pressure,
            "cycle_time": log.cycle_time,
            "error_code": log.error_code,
            "status": "normal" if not log.error_code else "error"
        }

        # 動的項目（Log.data）をフラットにマージ（Phase 2）
        if log.data:
            for key, value in log.data.items():
                realtime.setdefault(key, value)

        return realtime


class DailyLogSummarySerializer:
    """日次集計（DailyLogSummary）モデルのシリアライザー"""

    @staticmethod
    def to_dict(summary) -> dict:
        """
        DailyLogSummaryモデルを辞書に変換

        Args:
            summary: DailyLogSummaryモデルインスタンス

        Returns:
            dict: シリアライズされた日次集計データ
        """
        result = {
            "date": summary.date.isoformat(),
            "production_count": summary.production_count_total,
            "current_avg": summary.current_avg,
            "current_max": summary.current_max,
            "current_min": summary.current_min,
            "temperature_avg": summary.temperature_avg,
            "temperature_max": summary.temperature_max,
            "temperature_min": summary.temperature_min,
            "pressure_avg": summary.pressure_avg,
            "pressure_max": summary.pressure_max,
            "pressure_min": summary.pressure_min,
            "cycle_time_avg": summary.cycle_time_avg,
            "error_count": summary.error_count,
            "data_count": summary.data_count,
            # フロント(pages/equipment/[id].vue の logValue)は7d/30d(daily_summaries)で
            # 必ず `<data_type>_avg` を参照する。固定カラム production_count / cycle_time /
            # error_code はキー名が上記と不一致で7d/30dグラフの系列が空になっていたため、
            # current/temperature/pressure と同様に `<data_type>_avg` 別名を提供する。
            "production_count_avg": summary.production_count_total,
            "error_code_avg": summary.error_count,
        }

        # 動的項目の集計（data_summary）をマージ（Phase 2）
        if summary.data_summary:
            for key, value in summary.data_summary.items():
                result.setdefault(key, value)

        return result

    @staticmethod
    def to_list(summaries) -> List[dict]:
        """DailyLogSummaryモデルのリストを辞書のリストに変換"""
        return [DailyLogSummarySerializer.to_dict(s) for s in summaries]


class CommunicationErrorLogSerializer:
    """通信エラーログ（CommunicationErrorLog）モデルのシリアライザー"""

    @staticmethod
    def to_dict(log) -> dict:
        """
        CommunicationErrorLogモデルを辞書に変換

        Args:
            log: CommunicationErrorLogモデルインスタンス

        Returns:
            dict: シリアライズされたエラーログデータ
        """
        return {
            "id": log.id,
            "error_type": log.error_type,
            "error_message": log.error_message,
            "retry_count": log.retry_count,
            "plc_ip": log.plc_ip,
            "protocol": log.protocol,
            "occurred_at": log.occurred_at.isoformat(),
            "resolved_at": log.resolved_at.isoformat() if log.resolved_at else None
        }

    @staticmethod
    def to_list(logs) -> List[dict]:
        """CommunicationErrorLogモデルのリストを辞書のリストに変換"""
        return [CommunicationErrorLogSerializer.to_dict(log) for log in logs]


class AlarmHistorySerializer:
    """アラーム履歴（AlarmHistory）モデルのシリアライザー"""

    @staticmethod
    def to_dict(alarm) -> dict:
        """
        AlarmHistoryモデルを辞書に変換

        Args:
            alarm: AlarmHistoryモデルインスタンス

        Returns:
            dict: シリアライズされたアラームデータ
        """
        return {
            "id": alarm.id,
            "alarm_code": alarm.alarm_code,
            "alarm_level": alarm.alarm_level,
            "alarm_message": alarm.alarm_message,
            "alarm_data": alarm.alarm_data,
            "occurred_at": alarm.occurred_at.isoformat(),
            "cleared_at": alarm.cleared_at.isoformat() if alarm.cleared_at else None,
            "acknowledged": alarm.acknowledged
        }

    @staticmethod
    def to_list(alarms) -> List[dict]:
        """AlarmHistoryモデルのリストを辞書のリストに変換"""
        return [AlarmHistorySerializer.to_dict(alarm) for alarm in alarms]


class PLCStatusSerializer:
    """PLC状態（PLCStatus）モデルのシリアライザー"""

    @staticmethod
    def to_dict(plc_status, equipment_id: str) -> dict:
        """
        PLCStatusモデルを辞書に変換

        Args:
            plc_status: PLCStatusモデルインスタンス
            equipment_id: 設備ID文字列

        Returns:
            dict: シリアライズされたPLC状態データ
        """
        return {
            "equipment_id": equipment_id,
            "is_online": plc_status.is_online,
            "consecutive_errors": plc_status.consecutive_errors,
            "last_error_type": plc_status.last_error_type,
            "last_error_message": plc_status.last_error_message,
            "last_communication_at": plc_status.last_communication_at.isoformat() if plc_status.last_communication_at else None,
            "uptime_seconds": plc_status.uptime_seconds
        }

    @staticmethod
    def default_dict(equipment_id: str) -> dict:
        """PLCStatus未登録（未報告）設備の既定ステータスを返す。

        「まだ通信報告が無い」は正常状態であり、リソース不在(404)ではない。
        兄弟API（alarms/error_logs/incidents）が空データで200を返すのと整合させ、
        モデル既定（is_online=False, consecutive_errors=0, uptime_seconds=0）を反映する。
        never_reported=True で「実報告」と区別できるようにする（未使用クライアントは無視可）。
        """
        return {
            "equipment_id": equipment_id,
            "is_online": False,
            "consecutive_errors": 0,
            "last_error_type": None,
            "last_error_message": None,
            "last_communication_at": None,
            "uptime_seconds": 0,
            "never_reported": True,
        }
