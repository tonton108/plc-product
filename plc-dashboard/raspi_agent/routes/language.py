"""
言語切替ルート

Phase 7リファクタリング: agent_app.pyから分割
"""

from flask import Blueprint, redirect, request, url_for, make_response, current_app

language_bp = Blueprint('language', __name__)


@language_bp.route("/change_language/<lang>")
def change_language(lang):
    """言語を切り替え

    Args:
        lang: 言語コード（ja, en, zh）

    Returns:
        Response: リダイレクトレスポンス（クッキーに言語設定を保存）
    """
    if lang in current_app.config.get('LANGUAGES', {}):
        response = make_response(redirect(request.referrer or url_for('pages.index')))
        response.set_cookie('lang', lang, max_age=60*60*24*365)  # 1年間有効
        return response
    return redirect(request.referrer or url_for('pages.index'))
