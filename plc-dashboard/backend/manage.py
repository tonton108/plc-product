#!/usr/bin/env python3
"""
Flask アプリケーション起動スクリプト
Flask CLI（flask run）とdocker環境の両方に対応
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, get_socketio, db, wait_for_db

# アプリケーション作成
app, socketio = create_app()

# Flask CLIでの起動用（flask --app manage.py run）
def create_app_cli():
    """Flask CLIで起動する際のアプリケーション作成"""
    with app.app_context():
        wait_for_db(db.session)
    return app

# Flask CLIとの互換性のため、appを公開
app = create_app_cli()

if __name__ == "__main__":
    # 直接実行時（python manage.py または docker環境）
    port = int(os.environ.get("PORT", 5000))

    with app.app_context():
        wait_for_db(db.session)

    print(f"🚀 Starting Flask-SocketIO server on port {port}")
    socketio.run(
        app,
        debug=True,
        host="0.0.0.0",
        port=port,
        allow_unsafe_werkzeug=True  # 開発環境用
    )
