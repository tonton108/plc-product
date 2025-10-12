from flask import Flask
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv
from db import db
from flask_cors import CORS

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
    if database_url and database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
    elif not database_url:
        # DATABASE_URLが設定されていない場合はSQLiteを使用
        database_url = 'sqlite:///instance/plc_monitoring.db'

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # SQLAlchemyのエンジン設定を完全に同期モードに設定
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'echo': False,
        'connect_args': {
            'check_same_thread': False,  # SQLite用：マルチスレッド対応
        } if 'sqlite' in database_url else {}
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

    # ✅ モデルとルートをここでインポート
    from db import models
    from api.routes import register_routes
    register_routes(app, socketio)  # socketioを渡す

    print(f"✅ Registered tables: {db.Model.metadata.tables.keys()}")
    print(f"✅ URL Map:\n{app.url_map}")
    print(f"✅ Socket.IO initialized with threading mode")

    return app, socketio  # socketioも一緒に返す

def get_socketio():
    """socketioインスタンスを取得"""
    return socketio

def periodic_log_fetch():
    print("📡 periodic_log_fetch started (dummy)")

def wait_for_db(session):
    import time
    from sqlalchemy import text
    while True:
        try:
            # SQLAlchemy 2.x対応: textを使用
            session.execute(text("SELECT 1"))
            session.commit()  # トランザクションをコミット
            print("✅ データベース接続確認完了")
            break
        except Exception as e:
            time.sleep(1)
            print(f"Waiting for DB... ({e})")

__all__ = ["create_app", "get_socketio", "db", "periodic_log_fetch", "wait_for_db"]
