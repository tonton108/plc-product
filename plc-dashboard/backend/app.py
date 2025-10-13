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
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,      # 接続の健全性確認
            'pool_recycle': 300,        # 300秒で接続をリサイクル
            'pool_size': 10,            # 通常の接続プールサイズ
            'max_overflow': 20,         # 最大追加接続数
            'pool_timeout': 30,         # 接続タイムアウト(秒)
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

    # ✅ モデルとルートをここでインポート
    from db import models
    from api.routes import register_routes
    from error_handlers import register_error_handlers

    register_routes(app, socketio)  # socketioを渡す
    register_error_handlers(app)  # エラーハンドラーを登録

    print(f"✅ Registered tables: {db.Model.metadata.tables.keys()}")
    print(f"✅ URL Map:\n{app.url_map}")
    print(f"✅ Socket.IO initialized with threading mode")
    print(f"✅ Error handlers registered")

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
