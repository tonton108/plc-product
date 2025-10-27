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

    # Electron環境からDATABASE_PORTが渡された場合（PostgreSQL Portable使用時）
    database_port = os.getenv("DATABASE_PORT")
    if database_port and not database_url:
        # PostgreSQL Portable用の接続URL（ユーザー: postgres, パスワードなし, DB: postgres）
        database_url = f"postgresql+psycopg2://postgres@localhost:{database_port}/postgres"
        print(f"[App] PostgreSQL Portable接続: {database_url}")
    elif database_url and database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
    elif not database_url:
        # DATABASE_URLが設定されていない場合はSQLiteを使用（絶対パス）
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'plc_monitoring.db')
        database_url = f'sqlite:///{db_path}'

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

    #  モデルとルートをここでインポート
    from db import models
    from api.routes import register_routes
    from error_handlers import register_error_handlers

    register_routes(app, socketio)  # socketioを渡す
    # register_error_handlers(app)  # エラーハンドラーを一時的に無効化してエラー詳細を確認

    print(f" Registered tables: {db.Model.metadata.tables.keys()}")
    print(f" URL Map:\n{app.url_map}")
    print(f" Socket.IO initialized with threading mode")
    print(f" Error handlers registered")

    # データベーステーブルを自動作成（開発環境・PostgreSQL Portable用）
    # AUTO_CREATE_TABLESが設定されている、またはDATABASE_PORTが設定されている場合
    if os.getenv("AUTO_CREATE_TABLES") == "1" or os.getenv("DATABASE_PORT"):
        with app.app_context():
            print(f"[App] データベーステーブルを自動作成中...")
            db.create_all()
            print(f"[App] テーブル作成完了")

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
            print(" データベース接続確認完了")
            break
        except Exception as e:
            time.sleep(1)
            print(f"Waiting for DB... ({e})")

__all__ = ["create_app", "get_socketio", "db", "wait_for_db"]
