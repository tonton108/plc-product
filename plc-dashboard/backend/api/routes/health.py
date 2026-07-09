"""
ヘルスチェックAPI

アプリケーションの正常性確認エンドポイントを提供します。
唯一の無認証エンドポイント（死活監視・CI起動待ち用）。
"""

from flask import Blueprint, jsonify
from sqlalchemy import text

from db import db

health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route("/health", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント

    DB疎通まで確認する（プロセス起動だけでなく「使える状態」を保証する。
    CIの起動待ちはこの200を条件にしているため、DB未接続では503を返す）
    """
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "message": "OK", "database": "connected"}), 200
    except Exception:
        return jsonify({"status": "unhealthy", "database": "disconnected"}), 503
