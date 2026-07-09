from flask import Flask
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
import logging
from dotenv import load_dotenv
from db import db
from flask_cors import CORS
from api.constants import (
    DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT, DB_POOL_RECYCLE
)

# Phase 14: ロギング設定
logger = logging.getLogger(__name__)

load_dotenv()

migrate = Migrate()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)

    # CORS設定を環境変数から取得
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3001')
    allowed_origins = [origin.strip() for origin in cors_origins.split(',')]
    CORS(app, origins=allowed_origins)

    database_url = os.getenv("DATABASE_URL")

    # Electron環境からDATABASE_PORTが渡された場合（PostgreSQL Portable使用時）
    database_port = os.getenv("DATABASE_PORT")
    if database_port and not database_url:
        # PostgreSQL Portable用の接続URL（ユーザー: postgres, パスワードなし, DB: postgres）
        database_url = f"postgresql+psycopg2://postgres@localhost:{database_port}/postgres"
        logger.info(f"PostgreSQL Portable接続: {database_url}")
    elif database_url and database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
    elif not database_url:
        # DATABASE_URLが設定されていない場合はSQLiteを使用（絶対パス）
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'plc_monitoring.db')
        database_url = f'sqlite:///{db_path}'

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # SECRET_KEY: 既知の弱い固定デフォルト('dev-secret-key')は廃止（Phase 1）。
    # 未設定時は起動ごとのランダム値を使う（認証トークンはDB照合方式のため
    # SECRET_KEYに依存せず、再起動でセッションが無効になる副作用もない）
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        import secrets
        secret_key = secrets.token_hex(32)
        logger.warning("SECRET_KEYが未設定のため、起動ごとのランダム値を使用します（本番では必ず環境変数で設定してください）")
    app.config['SECRET_KEY'] = secret_key

    # SQLAlchemyのエンジン設定（データベースごとに最適化）
    if 'sqlite' in database_url:
        # SQLite用の設定（プール設定は使用しない）
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'echo': False,
            'connect_args': {
                'check_same_thread': False,  # マルチスレッド対応
            }
        }
    else:
        # PostgreSQL/MySQL用の設定（接続プールを最適化）
        # 200台規模に対応した設定（Phase 15: 定数を使用）
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,              # 接続の健全性確認
            'pool_recycle': DB_POOL_RECYCLE,    # 接続をリサイクルする間隔（秒）
            'pool_size': DB_POOL_SIZE,          # 通常の接続プールサイズ
            'max_overflow': DB_MAX_OVERFLOW,    # 最大追加接続数
            'pool_timeout': DB_POOL_TIMEOUT,    # 接続タイムアウト(秒)
            'echo': False,
        }

    db.init_app(app)
    migrate.init_app(app, db)
    
    # Socket.IO初期化（threading modeでgreenletエラーを回避）
    socketio.init_app(
        app,
        cors_allowed_origins=allowed_origins,
        async_mode='threading',
        logger=False,
        engineio_logger=False
    )

    #  モデルとルートをここでインポート
    from db import models
    from api.routes import register_routes
    from error_handlers import register_error_handlers

    register_routes(app, socketio)  # socketioを渡す
    register_error_handlers(app)

    # 認証管理CLIコマンドを登録（flask auth ...）
    from api.cli import register_cli
    register_cli(app)

    logger.debug(f"Registered tables: {db.Model.metadata.tables.keys()}")
    logger.debug(f"URL Map:\n{app.url_map}")
    logger.info("Socket.IO initialized with threading mode")
    logger.info("Error handlers registered")

    # データベーステーブルを自動作成（開発環境・PostgreSQL Portable用）
    # AUTO_CREATE_TABLESが設定されている、またはDATABASE_PORTが設定されている場合
    if os.getenv("AUTO_CREATE_TABLES") == "1" or os.getenv("DATABASE_PORT"):
        with app.app_context():
            logger.info("データベーステーブルを自動作成中...")
            db.create_all()
            logger.info("テーブル作成完了")

    return app, socketio  # socketioも一緒に返す

def get_socketio():
    """socketioインスタンスを取得"""
    return socketio

def wait_for_db(session):
    import time
    from sqlalchemy import text
    while True:
        try:
            # SQLAlchemy 2.x対応: textを使用
            session.execute(text("SELECT 1"))
            session.commit()  # トランザクションをコミット
            logger.info("データベース接続確認完了")
            break
        except Exception as e:
            time.sleep(1)
            logger.warning(f"Waiting for DB... ({e})")

__all__ = ["create_app", "get_socketio", "db", "wait_for_db"]
