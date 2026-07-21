"""
ログ管理API

PLCログデータの保存・取得に関するエンドポイントを提供します。
WebSocketによるリアルタイム配信機能も含みます。

Phase 6リファクタリング: 共通Helperを使用
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, timezone
import logging

from db import db
from db.models import Equipment, Log, DailyLogSummary, SetupStatus, OperationalStatus, PLCStatus
from db.models.logs import FIXED_LOG_FIELDS, LOG_META_FIELDS
from api.serializers import LogSerializer, DailyLogSummarySerializer
from api.helpers import get_equipment_or_404, handle_api_errors
from api.auth_service import require_user, require_api_key

logger = logging.getLogger(__name__)

logs_bp = Blueprint('logs', __name__, url_prefix='/api')

# SocketIOインスタンスを保持（websocket.pyから設定される）
_socketio = None


def set_socketio(socketio):
    """SocketIOインスタンスを設定"""
    global _socketio
    _socketio = socketio


def get_socketio():
    """SocketIOインスタンスを取得"""
    return _socketio


@logs_bp.route("/logs", methods=["POST"])
@require_api_key
def save_log_data():
    """ログデータをDBに保存 + WebSocketでリアルタイム配信"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        equipment_id = data.get("equipment_id")
        if not equipment_id:
            return jsonify({"error": "equipment_id is required"}), 400

        logger.info(f"PLCデータ受信: 設備ID={equipment_id}, タイムスタンプ={data.get('timestamp')}")

        # 設備の存在確認
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        # タイムスタンプの処理
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif timestamp is None:
            timestamp = datetime.now(timezone.utc)

        try:
            # ログエントリを作成
            log_entry = Log()
            log_entry.equipment_id = equipment.id
            log_entry.timestamp = timestamp
            log_entry.production_count = data.get("production_count")
            log_entry.current = data.get("current")
            log_entry.temperature = data.get("temperature")
            log_entry.pressure = data.get("pressure")
            log_entry.cycle_time = data.get("cycle_time")
            log_entry.error_code = data.get("error_code")

            # 固定カラム・メタキー以外の受信項目を動的項目として data(JSON) に保存
            # （設備ごとに任意項目を定義できる仕様の中核。Phase 2）
            reserved = set(FIXED_LOG_FIELDS) | set(LOG_META_FIELDS)
            dynamic_data = {k: v for k, v in data.items() if k not in reserved}
            log_entry.data = dynamic_data or None

            db.session.add(log_entry)

            # 初回データ受信時にセットアップ完了
            if equipment.setup_status == SetupStatus.PLC_CONFIGURED:
                equipment.setup_status = SetupStatus.SETUP_COMPLETE
                logger.info(f"セットアップ完了: {equipment_id}")

            # 運用ステータスを「稼働中」に更新
            if equipment.operational_status != OperationalStatus.RUNNING:
                equipment.operational_status = OperationalStatus.RUNNING
                logger.info(f"運用ステータスを稼働中に更新: {equipment_id}")

            now = datetime.now(timezone.utc)
            equipment.updated_at = now

            # PLC通信状態を「オンライン」に回復する。データPOST成功＝PLCと通信でき
            # ている証左のため、last_communication_at を更新し、エラー経路(save_error_log)
            # で False にされた is_online と累積した consecutive_errors をリセットする。
            # 従来はこの回復経路が本番コードに一切存在せず、一度でも通信エラーが起きた
            # 設備は復旧後も永久にオフライン表示・エラー数累積のままで、
            # last_communication_at も常にNULLだった。状態変更時刻はオフライン→
            # オンラインの遷移時のみ更新する（毎POSTでの無意味な更新を避ける）。
            plc_status = PLCStatus.query.filter_by(equipment_id=equipment.id).first()
            if plc_status:
                if not plc_status.is_online:
                    plc_status.last_status_change_at = now
                plc_status.is_online = True
                plc_status.consecutive_errors = 0
                plc_status.last_communication_at = now

            db.session.commit()

            logger.debug(f"DB保存完了: ログID={log_entry.id}")

        except Exception as db_error:
            db.session.rollback()
            logger.error(f"DB保存エラー: {db_error}", exc_info=True)
            return jsonify({"error": f"Database error: {str(db_error)}"}), 500

        # WebSocketでリアルタイム配信
        socketio = get_socketio()
        if socketio:
            # 固定項目＋動的項目をシリアライザで一元的に構築（保存したlog_entryから）
            realtime_data = LogSerializer.to_realtime(log_entry, equipment_id)

            try:
                # 設備別room宛てに配信（Phase 3）。
                # 旧実装は to='monitoring'（全体）で、全クライアントが全設備の更新を
                # 受信しクライアント側で捨てていた（200台×20画面で20倍の増幅）。
                # 表示中の設備のみが参加する equipment_{id} room に限定する
                room = f"equipment_{equipment_id}"
                socketio.emit('plc_data_update', realtime_data, to=room)
                logger.debug(f"WebSocket送信完了: {room}")
            except Exception as ws_error:
                logger.warning(f"WebSocket送信エラー (処理継続): {ws_error}")

        return jsonify({
            "message": "Data saved and broadcasted",
            "saved_to_db": True,
            "broadcasted_to_ui": bool(socketio),
            "timestamp": timestamp.isoformat()
        }), 200

    except Exception as e:
        logger.error(f"PLCデータ処理エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@logs_bp.route("/logs/<equipment_id>/latest", methods=["GET"])
@require_user()
@handle_api_errors
def get_latest_data(equipment_id):
    """最新データ取得（初期表示用）- Phase 6: 共通Helper使用"""
    equipment = get_equipment_or_404(equipment_id)

    latest_log = Log.query.filter_by(equipment_id=equipment.id)\
                          .order_by(Log.id.desc())\
                          .first()

    if not latest_log:
        return jsonify({"message": "No data found"}), 404

    data = LogSerializer.to_dict(latest_log)
    data["equipment_id"] = equipment_id
    return jsonify(data), 200


@logs_bp.route("/logs/<equipment_id>/history", methods=["GET"])
@require_user()
@handle_api_errors
def get_history_data(equipment_id):
    """履歴データ取得（グラフ表示用）- Phase 6: 共通Helper使用"""
    equipment = get_equipment_or_404(equipment_id)

    limit = min(request.args.get('limit', 100, type=int), 10000)

    logs = Log.query.filter_by(equipment_id=equipment.id)\
                   .order_by(Log.id.desc())\
                   .limit(limit)\
                   .all()

    return jsonify({
        "equipment_id": equipment_id,
        "data": LogSerializer.to_list(logs),
        "total_records": len(logs)
    }), 200


@logs_bp.route("/logs/<equipment_id>/history_optimized", methods=["GET"])
@require_user()
@handle_api_errors
def get_history_data_optimized(equipment_id):
    """最適化された履歴データ取得 - Phase 6: 共通Helper使用"""
    equipment = get_equipment_or_404(equipment_id)

    limit = min(request.args.get('limit', 100, type=int), 10000)
    period = request.args.get('period', '1h')

    VALID_PERIODS = {'1h', '6h', '24h', '7d', '30d'}
    if period not in VALID_PERIODS:
        return jsonify({"error": f"Invalid period. Must be one of: {', '.join(sorted(VALID_PERIODS))}"}), 400

    if period in ['1h', '6h', '24h']:
        # 短期間は詳細データ
        time_map = {'1h': 1, '6h': 6, '24h': 24}
        start_time = datetime.now(timezone.utc) - timedelta(hours=time_map[period])

        logs = Log.query.filter(
            Log.equipment_id == equipment.id,
            Log.timestamp >= start_time
        ).order_by(Log.timestamp.desc()).limit(limit).all()

        data = LogSerializer.to_list(logs)
        data_source = "raw_logs"

    elif period in ['7d', '30d']:
        # 長期間は日次集計データ
        days_map = {'7d': 7, '30d': 30}
        start_date = (datetime.now(timezone.utc) - timedelta(days=days_map[period])).date()

        summaries = db.session.query(DailyLogSummary)\
            .filter_by(equipment_id=equipment.id)\
            .filter(DailyLogSummary.date >= start_date)\
            .order_by(DailyLogSummary.date.desc())\
            .all()

        data = DailyLogSummarySerializer.to_list(summaries)
        data_source = "daily_summaries"

    return jsonify({
        "equipment_id": equipment_id,
        "period": period,
        "data_source": data_source,
        "data": data,
        "total_records": len(data)
    }), 200
