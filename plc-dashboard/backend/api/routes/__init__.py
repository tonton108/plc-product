"""
APIルートモジュール

このパッケージは機能別に分割されたAPIルートを提供します。

使用例（推奨）:
    from api.routes import register_all_routes

    def create_app():
        app = Flask(__name__)
        socketio = SocketIO(app)
        register_all_routes(app, socketio)
        return app, socketio

使用例（後方互換性）:
    from api.routes import register_routes
    register_routes(app, socketio)
"""

import logging

from api.routes.auth import auth_bp
from api.routes.equipment import equipment_bp
from api.routes.logs import logs_bp
from api.routes.admin import admin_bp
from api.routes.users import users_bp
from api.routes.errors_alarms import errors_alarms_bp
from api.routes.health import health_bp
from api.routes.websocket import register_websocket_handlers
from api.scheduler import start_cleanup_scheduler

logger = logging.getLogger(__name__)


def register_all_routes(app, socketio=None):
    """
    すべてのAPIルートを登録

    Args:
        app: Flaskアプリケーションインスタンス
        socketio: Flask-SocketIOインスタンス（オプション）
    """
    # Blueprintを登録
    app.register_blueprint(auth_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(errors_alarms_bp)
    app.register_blueprint(health_bp)

    # WebSocketハンドラを登録
    if socketio:
        register_websocket_handlers(socketio)


def register_routes(app, socketio=None):
    """
    すべてのAPIルートを登録（後方互換性のためのラッパー）

    Args:
        app: Flaskアプリケーションインスタンス
        socketio: Flask-SocketIOインスタンス（オプション）

    Note:
        この関数は後方互換性のために維持されています。
        内部的には register_all_routes() を呼び出します。
    """
    logger.debug("===== APIルート登録開始 =====")
    logger.debug(f"Flask app: {app}")
    logger.debug(f"SocketIO: {socketio}")

    # ルート登録
    register_all_routes(app, socketio)

    # スケジューラー開始
    start_cleanup_scheduler(app)

    # APIルート登録完了ログ
    logger.debug("===== APIルート登録完了 =====")
    logger.debug("登録されたルート:")
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api/'):
            logger.debug(f"    {rule.methods} {rule.rule}")
    logger.debug("==========================")


# 後方互換性のためのエクスポート
__all__ = [
    'register_all_routes',
    'register_routes',  # 後方互換性エイリアス
    'auth_bp',
    'equipment_bp',
    'logs_bp',
    'admin_bp',
    'users_bp',
    'errors_alarms_bp',
    'health_bp',
    'register_websocket_handlers'
]
