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
    # SQLiteの場合はwait_for_dbをスキップ
    # with app.app_context():
    #     wait_for_db(db.session)
    return app

# Flask CLIとの互換性のため、appを公開
app = create_app_cli()

if __name__ == "__main__":
    # セキュリティチェック（本番環境のみ）
    flask_env = os.environ.get("FLASK_ENV", "development")
    if flask_env == "production":
        print("セキュリティ設定をチェックしています...")
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "..", "scripts", "check_security.py")],
            capture_output=False
        )
        if result.returncode != 0:
            print("セキュリティチェックに失敗しました。デフォルトパスワードを変更してください。")
            print("   起動を中止します。")
            sys.exit(1)
        print(" セキュリティチェック完了")
        print()

    # 直接実行時（python manage.py または docker環境）
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"  # FLASK_DEBUGが"0"なら無効化

    # SQLiteの場合はwait_for_dbをスキップ
    # with app.app_context():
    #     wait_for_db(db.session)

    print(f"Starting Flask-SocketIO server on port {port} (debug={debug_mode})")
    socketio.run(
        app,
        debug=debug_mode,
        use_reloader=False,  # 自動リローダーを完全に無効化
        host="0.0.0.0",
        port=port,
        allow_unsafe_werkzeug=debug_mode  # 開発環境のみ許可
    )
