"""
管理API

データベースのクリーンアップ、統計情報、集計データ作成などの
管理機能に関するエンドポイントを提供します。
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import threading
import logging

from db import db
from db.models import Equipment, Log, DailyLogSummary, MonthlyLogSummary
from api.scheduler import (
    cleanup_old_logs,
    backfill_incident_aftermath,
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

        # daysの入力検証。非正値/非整数は不可（パーティション化環境では
        # cutoffが未来になり保持期間内のパーティションを不可逆にDROPしうるため、
        # 危険な入力は400で弾く）。
        if not isinstance(days, int) or isinstance(days, bool) or days < 1:
            return jsonify({"error": "days must be a positive integer"}), 400

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        old_logs_count = Log.query.filter(Log.timestamp < cutoff_date).count()

        if old_logs_count == 0:
            return jsonify({"message": "削除対象のログはありません", "deleted_count": 0}), 200

        # バックグラウンドでクリーンアップ実行。
        # リクエストのdaysを削除本体にも渡す（旧実装はcountはdays基準・削除は
        # 設定値raw_data_days基準で不整合だった。Phase 3で統一）。
        app = current_app._get_current_object()

        def _run_cleanup():
            with app.app_context():
                # 生ログ削除前にインシデントの発生後ウィンドウを後追い保存する。
                # スケジューラの定期実行を待たずに手動削除する場合でも、未捕捉の
                # 発生後ログを取りこぼさないため（SPEC §5.2）。
                backfill_incident_aftermath()
                cleanup_old_logs(retention_days=days)

        threading.Thread(target=_run_cleanup, daemon=True).start()

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

        # 別スレッドではアプリコンテキストが無いためDBアクセスできない。
        # current_appを取り出して各スレッドでapp_contextを張る（Phase 3）。
        app = current_app._get_current_object()

        if summary_type == 'daily':
            target_date = data.get('date')
            if target_date:
                target_date = datetime.fromisoformat(target_date).date()
            else:
                target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

            def _run_daily():
                with app.app_context():
                    create_daily_summary(target_date)

            threading.Thread(target=_run_daily, daemon=True).start()
            return jsonify({"message": f"{target_date}の日次集計を開始しました"}), 200

        elif summary_type == 'monthly':
            year = data.get('year', datetime.now(timezone.utc).year)
            month = data.get('month', datetime.now(timezone.utc).month)

            def _run_monthly():
                with app.app_context():
                    create_monthly_summary(year, month)

            threading.Thread(target=_run_monthly, daemon=True).start()
            return jsonify({"message": f"{year}年{month}月の月次集計を開始しました"}), 200

        else:
            return jsonify({"error": "Invalid summary type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
