"""
WSGI entry point for production deployment with Gunicorn

Usage:
    gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
             --workers 4 \
             --bind 0.0.0.0:5000 \
             wsgi:app
"""
from app import create_app

app, socketio = create_app()

if __name__ == "__main__":
    # 開発モードでの実行用（本番ではgunicornを使用）
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
