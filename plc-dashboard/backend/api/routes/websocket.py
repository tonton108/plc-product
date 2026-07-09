"""
WebSocket管理モジュール

Socket.IOによるリアルタイム通信のハンドラーを提供します。

Phase 5最適化: 複数クエリをJOIN/サブクエリで統合
"""

from flask import current_app
from flask_socketio import emit, join_room, leave_room
from sqlalchemy import func
import logging

from db import db
from db.models import Equipment, Log
from api.serializers import LogSerializer

logger = logging.getLogger(__name__)

# グローバルなSocketIOインスタンス参照
_socketio_instance = None


def register_websocket_handlers(socketio):
    """
    WebSocketイベントハンドラを登録

    Args:
        socketio: Flask-SocketIOインスタンス
    """
    global _socketio_instance
    _socketio_instance = socketio

    # logs.pyにもSocketIOインスタンスを設定
    from api.routes.logs import set_socketio
    set_socketio(socketio)

    @socketio.on('join_monitoring')
    def on_join_monitoring(data):
        """NuxtUIからのモニタリング接続"""
        join_room('monitoring')
        equipment_id = data.get('equipment_id')
        if equipment_id:
            join_room(f'equipment_{equipment_id}')
        emit('status', {'msg': 'Connected to monitoring', 'room': 'monitoring'})

    @socketio.on('leave_monitoring')
    def on_leave_monitoring(data):
        """モニタリング画面の切断"""
        leave_room('monitoring')
        equipment_id = data.get('equipment_id')
        if equipment_id:
            leave_room(f'equipment_{equipment_id}')
        emit('status', {'msg': 'Left monitoring room'})

    @socketio.on('connect')
    def on_connect(auth=None):
        """WebSocket接続確立（Phase 1: ハンドシェイクのトークン認証必須）

        クライアントは io(url, { auth: { token } }) でBearerトークンを渡す。
        無効なら False を返して接続を拒否する。
        """
        from api.auth_service import authenticate_socketio_connect

        user = authenticate_socketio_connect(auth)
        if user is None:
            logger.warning('Socket.IO接続を拒否しました（トークン無効または未指定）')
            return False

        emit('status', {'msg': 'Connected to PLC monitoring system'})
        logger.info(f'NuxtUI client connected (user={user.username})')

    @socketio.on('disconnect')
    def on_disconnect():
        """WebSocket接続切断"""
        logger.info('NuxtUI client disconnected')

    @socketio.on('get_realtime_status')
    def on_get_realtime_status(data):
        """リアルタイム状態取得要求

        Phase 5最適化: 2クエリ → サブクエリで1クエリに統合
        - 旧方式: Equipment取得 → Log取得 (2クエリ)
        - 新方式: JOINとサブクエリで1クエリ
        """
        try:
            with current_app.app_context():
                equipment_id = data.get('equipment_id')
                if equipment_id:
                    # サブクエリで最新のLog IDを取得し、JOINで一括取得
                    # 1クエリでEquipmentと最新Logを同時取得
                    latest_log_subq = db.session.query(
                        Log.equipment_id,
                        func.max(Log.id).label('max_id')
                    ).group_by(Log.equipment_id).subquery()

                    result = db.session.query(Equipment, Log).join(
                        latest_log_subq,
                        Equipment.id == latest_log_subq.c.equipment_id
                    ).join(
                        Log,
                        Log.id == latest_log_subq.c.max_id
                    ).filter(
                        Equipment.equipment_id == equipment_id
                    ).first()

                    if result:
                        equipment, latest_log = result
                        response_data = LogSerializer.to_realtime(latest_log, equipment_id)
                        emit('realtime_status', response_data)
        except Exception as e:
            logger.error(f"get_realtime_status エラー: {e}")
            emit('error', {'msg': 'Failed to get status'})

    logger.info("WebSocketハンドラを登録しました")


def get_socketio():
    """グローバルなSocketIOインスタンスを取得"""
    return _socketio_instance
