"""
REST APIエンドポイント

Phase 7リファクタリング: agent_app.pyから分割

注意: このモジュールはBlueprintとして定義していますが、
agent_app.pyの既存構造との互換性のため、一部の機能は
agent_app.pyに残しています。

将来的には完全なBlueprint化を目指します。
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import random
import time

from auth.authentication import require_auth, verify_password, get_current_admin_password_hash
from config.plc_config import SERIES_LIST

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route("/series")
@require_auth
def api_series():
    """PLCシリーズ一覧を取得

    Query Parameters:
        manufacturer: メーカー名

    Returns:
        JSON: シリーズ一覧
    """
    manufacturer = request.args.get("manufacturer", "")
    return jsonify(SERIES_LIST.get(manufacturer, []))


@api_bp.route("/verify-password", methods=["POST"])
@require_auth
def api_verify_password():
    """設定変更時のパスワード確認（Phase 6セキュリティ修正）

    Request Body:
        password: 確認するパスワード

    Returns:
        JSON: {"success": bool, "error": str?}
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "無効なリクエスト"}), 400

    password = data.get("password", "")
    current_hash = get_current_admin_password_hash()

    # 現在ログインしているユーザーのパスワードと照合
    if current_hash and verify_password(password, current_hash):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "パスワードが正しくありません"})


# 以下のAPIはagent_app.pyに残す（グローバル変数への依存があるため）
# - /api/logs - config.load_plc_config()への依存
# - /api/plc-agent/* - plc_agent_thread, plc_agent_stop_eventへの依存
# - /api/equipment/* - 複雑なDB操作
# - /api/current-equipment-info - 複数の依存関係

# これらは将来的に依存性注入パターンを使用してBlueprintに移行予定
