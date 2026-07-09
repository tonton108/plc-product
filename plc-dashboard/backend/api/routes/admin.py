"""
管理API

データベースのクリーンアップ、統計情報、集計データ作成などの
管理機能に関するエンドポイントを提供します。
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import threading
import logging

from db import db
from db.models import Equipment, Log, DailyLogSummary, MonthlyLogSummary
from api.scheduler import (
    cleanup_old_logs,
    create_daily_summary,
    create_monthly_summary,
    DATA_RETENTION_CONFIG
)
from api.auth_service import require_user
from db.models import UserRoles

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route("/cleanup", methods=["POST"])
@require_user(role=UserRoles.ADMIN)
def manual_cleanup():
    """手動クリーンアップ実行"""
    try:
        data = request.get_json() or {}
        days = data.get('days', DATA_RETENTION_CONFIG['raw_data_days'])

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        old_logs_count = Log.query.filter(Log.timestamp < cutoff_date).count()

        if old_logs_count == 0:
            return jsonify({"message": "削除対象のログはありません", "deleted_count": 0}), 200

        # バックグラウンドでクリーンアップ実行
        threading.Thread(target=cleanup_old_logs, daemon=True).start()

        return jsonify({
            "message": f"クリーンアップを開始しました ({old_logs_count}件対象)",
            "estimated_count": old_logs_count
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/stats", methods=["GET"])
@require_user(role=UserRoles.ADMIN)
def get_database_stats():
    """データベース統計情報を取得"""
    try:
        total_logs = Log.query.count()
        total_equipments = Equipment.query.count()
        total_daily_summaries = DailyLogSummary.query.count()
        total_monthly_summaries = MonthlyLogSummary.query.count()

        # 最古・最新のログ
        oldest_log = Log.query.order_by(Log.timestamp.asc()).first()
        newest_log = Log.query.order_by(Log.timestamp.desc()).first()

        # 設備別ログ数（N+1問題を回避するため、1クエリで取得）
        equipment_log_counts = db.session.query(
            Equipment.equipment_id,
            func.count(Log.id).label('log_count')
        ).outerjoin(Log, Equipment.id == Log.equipment_id)\
         .group_by(Equipment.id, Equipment.equipment_id)\
         .all()

        equipment_stats = [
            {
                "equipment_id": eq_id,
                "log_count": log_count
            }
            for eq_id, log_count in equipment_log_counts
        ]

        return jsonify({
            "total_logs": total_logs,
            "total_equipments": total_equipments,
            "total_daily_summaries": total_daily_summaries,
            "total_monthly_summaries": total_monthly_summaries,
            "oldest_log": oldest_log.timestamp.isoformat() if oldest_log else None,
            "newest_log": newest_log.timestamp.isoformat() if newest_log else None,
            "equipment_stats": equipment_stats,
            "retention_config": DATA_RETENTION_CONFIG
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/create_summary", methods=["POST"])
@require_user(role=UserRoles.ADMIN)
def manual_create_summary():
    """手動で集計データ作成"""
    try:
        data = request.get_json() or {}
        summary_type = data.get('type', 'daily')  # 'daily' or 'monthly'

        if summary_type == 'daily':
            target_date = data.get('date')
            if target_date:
                target_date = datetime.fromisoformat(target_date).date()
            else:
                target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

            threading.Thread(target=create_daily_summary, args=(target_date,), daemon=True).start()
            return jsonify({"message": f"{target_date}の日次集計を開始しました"}), 200

        elif summary_type == 'monthly':
            year = data.get('year', datetime.now(timezone.utc).year)
            month = data.get('month', datetime.now(timezone.utc).month)

            threading.Thread(target=create_monthly_summary, args=(year, month), daemon=True).start()
            return jsonify({"message": f"{year}年{month}月の月次集計を開始しました"}), 200

        else:
            return jsonify({"error": "Invalid summary type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
