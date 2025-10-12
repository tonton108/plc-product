import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, get_socketio, db, periodic_log_fetch, wait_for_db
import threading

app, socketio = create_app()  # 戻り値を2つ受け取る

# Flask-CLIでの起動用（flask --app manage.py run）
def create_app_cli():
    """Flask CLIで起動する際のアプリケーション作成"""
    with app.app_context():
        wait_for_db(db.session)
        threading.Thread(target=periodic_log_fetch, daemon=True).start()
    return app

# 開発用の直接起動関数（使用しない）
def runserver():
    with app.app_context():
        wait_for_db(db.session)
        threading.Thread(target=periodic_log_fetch, daemon=True).start()
        socketio.run(app, debug=True, host="0.0.0.0")  # eventletサーバーを使用

# Flask CLIとの互換性のため、appを公開
app = create_app_cli()

if __name__ == "__main__":
    runserver()
