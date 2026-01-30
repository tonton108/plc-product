"""
ヘルスチェックAPI

アプリケーションの正常性確認エンドポイントを提供します。
"""

from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route("/health", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({"status": "healthy", "message": "OK"}), 200
