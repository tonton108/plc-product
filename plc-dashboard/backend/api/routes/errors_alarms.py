"""
エラー・アラームAPI

PLC通信エラーログとアラーム履歴の管理に関するエンドポイントを提供します。
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import logging

from db import db
from db.models import (
    Equipment, CommunicationErrorLog, AlarmHistory, PLCStatus,
    ErrorTypes, AlarmLevels
)
from api.serializers import (
    CommunicationErrorLogSerializer,
    AlarmHistorySerializer,
    PLCStatusSerializer
)
from api.auth_service import require_user, require_api_key

logger = logging.getLogger(__name__)

errors_alarms_bp = Blueprint('errors_alarms', __name__, url_prefix='/api')


# ========================================
# エラーログAPI
# ========================================

@errors_alarms_bp.route("/equipment/<equipment_id>/error_logs", methods=["POST"])
@require_api_key
def save_error_log(equipment_id):
    """PLC通信エラーを記録（Raspberry Piエージェントから呼び出し）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        error_log = CommunicationErrorLog(
            equipment_id=equipment.id,
            error_type=data.get("error_type", ErrorTypes.UNKNOWN),
            error_message=data.get("error_message", ""),
            retry_count=data.get("retry_count", 0),
            plc_ip=data.get("plc_ip", equipment.plc_ip),
            protocol=data.get("protocol", equipment.protocol)
        )

        db.session.add(error_log)

        # PLC状態を更新
        plc_status = PLCStatus.query.filter_by(equipment_id=equipment.id).first()
        if plc_status:
            plc_status.consecutive_errors += 1
            plc_status.last_error_type = error_log.error_type
            plc_status.last_error_message = error_log.error_message
            plc_status.is_online = False
            plc_status.last_status_change_at = datetime.now(timezone.utc)

        db.session.commit()

        logger.info(f"エラー記録: {equipment_id} - {error_log.error_type}")

        return jsonify({"message": "エラーログを記録しました"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@errors_alarms_bp.route("/equipment/<equipment_id>/error_logs", methods=["GET"])
@require_user()
def get_error_logs(equipment_id):
    """エラーログ一覧を取得"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        limit = min(request.args.get('limit', 100, type=int), 1000)
        offset = request.args.get('offset', 0, type=int)

        error_logs = CommunicationErrorLog.query.filter_by(
            equipment_id=equipment.id
        ).order_by(CommunicationErrorLog.occurred_at.desc()).limit(limit).offset(offset).all()

        return jsonify(CommunicationErrorLogSerializer.to_list(error_logs)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@errors_alarms_bp.route("/equipment/<equipment_id>/error_logs/<int:error_log_id>/resolve", methods=["PATCH"])
@require_user()
def resolve_error_log(equipment_id, error_log_id):
    """エラーログを解決（resolve）する"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        error_log = CommunicationErrorLog.query.filter_by(
            id=error_log_id,
            equipment_id=equipment.id
        ).first()
        if not error_log:
            return jsonify({"error": "Error log not found"}), 404

        error_log.resolved_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(f"エラーログ解決完了: {equipment_id} / error_log_id={error_log_id}")

        return jsonify({
            "message": "エラーログを解決しました",
            "error_log_id": error_log_id
        }), 200

    except Exception as e:
        logger.error(f"エラーログ解決エラー: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ========================================
# アラームAPI
# ========================================

@errors_alarms_bp.route("/equipment/<equipment_id>/alarms", methods=["POST"])
@require_api_key
def save_alarm(equipment_id):
    """アラームを記録（Raspberry Piエージェントから呼び出し）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        alarm = AlarmHistory(
            equipment_id=equipment.id,
            alarm_code=data.get("alarm_code", "UNKNOWN"),
            alarm_level=data.get("alarm_level", AlarmLevels.WARNING),
            alarm_message=data.get("alarm_message", ""),
            alarm_data=data.get("alarm_data")
        )

        db.session.add(alarm)
        db.session.commit()

        logger.info(f"アラーム記録: {equipment_id} - {alarm.alarm_code} ({alarm.alarm_level})")

        return jsonify({"message": "アラームを記録しました", "alarm_id": alarm.id}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@errors_alarms_bp.route("/equipment/<equipment_id>/alarms", methods=["GET"])
@require_user()
def get_alarms(equipment_id):
    """アラーム履歴一覧を取得"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        limit = min(request.args.get('limit', 100, type=int), 1000)
        offset = request.args.get('offset', 0, type=int)

        alarms = AlarmHistory.query.filter_by(
            equipment_id=equipment.id
        ).order_by(AlarmHistory.occurred_at.desc()).limit(limit).offset(offset).all()

        return jsonify(AlarmHistorySerializer.to_list(alarms)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@errors_alarms_bp.route("/equipment/<equipment_id>/alarms/<int:alarm_id>/acknowledge", methods=["PATCH"])
@require_user()
def acknowledge_alarm(equipment_id, alarm_id):
    """アラームを確認（acknowledge）する"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        alarm = AlarmHistory.query.filter_by(
            id=alarm_id,
            equipment_id=equipment.id
        ).first()
        if not alarm:
            return jsonify({"error": "Alarm not found"}), 404

        data = request.get_json() or {}
        acknowledged_by = data.get("acknowledged_by", "System")

        alarm.acknowledged = True
        alarm.acknowledged_by = acknowledged_by
        alarm.acknowledged_at = datetime.now(timezone.utc)

        db.session.commit()

        logger.info(f"アラーム確認完了: {equipment_id} / alarm_id={alarm_id} / by={acknowledged_by}")

        return jsonify({
            "message": "アラームを確認しました",
            "alarm_id": alarm_id,
            "acknowledged_by": acknowledged_by
        }), 200

    except Exception as e:
        logger.error(f"アラーム確認エラー: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@errors_alarms_bp.route("/equipment/<equipment_id>/alarms/<int:alarm_id>/clear", methods=["PATCH"])
@require_user()
def clear_alarm(equipment_id, alarm_id):
    """アラームを解除（clear）する"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        alarm = AlarmHistory.query.filter_by(
            id=alarm_id,
            equipment_id=equipment.id
        ).first()
        if not alarm:
            return jsonify({"error": "Alarm not found"}), 404

        alarm.cleared_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(f"アラーム解除完了: {equipment_id} / alarm_id={alarm_id}")

        return jsonify({
            "message": "アラームを解除しました",
            "alarm_id": alarm_id
        }), 200

    except Exception as e:
        logger.error(f"アラーム解除エラー: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ========================================
# PLC状態API
# ========================================

@errors_alarms_bp.route("/equipment/<equipment_id>/plc_status", methods=["GET"])
@require_user()
def get_plc_status(equipment_id):
    """PLC通信状態を取得"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        plc_status = PLCStatus.query.filter_by(equipment_id=equipment.id).first()
        if not plc_status:
            return jsonify({"error": "PLC status not found"}), 404

        return jsonify(PLCStatusSerializer.to_dict(plc_status, equipment_id)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
