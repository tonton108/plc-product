from app import create_app, get_socketio
import os

app, socketio = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, debug=True, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
