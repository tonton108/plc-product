"""
Flask/Babel/SocketIO アプリケーション設定

Phase 7リファクタリング: agent_app.pyから分割

アプリケーションの初期化設定を一元管理します。
"""

import os
from flask import request
from flask_babel import Babel
from flask_socketio import SocketIO

# サポートされる言語
SUPPORTED_LANGUAGES = {
    'ja': '日本語',
    'en': 'English',
    'zh': '中文'
}

# グローバルインスタンス（init_app_config後に設定）
_babel = None
_socketio = None


def get_locale():
    """現在の言語を取得（クッキー > ブラウザ設定）

    優先順位:
    1. クッキーに保存された言語設定
    2. ブラウザのAccept-Languageヘッダー
    3. デフォルト（日本語）
    """
    from flask import current_app

    # クッキーから言語を取得
    lang = request.cookies.get('lang')
    if lang in SUPPORTED_LANGUAGES:
        return lang

    # ブラウザの言語設定から最適な言語を選択
    return request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys()) or 'ja'


def init_app_config(app):
    """Flaskアプリケーションの設定を初期化

    Args:
        app: Flaskアプリケーションインスタンス

    Returns:
        tuple: (socketio, babel) インスタンス
    """
    global _babel, _socketio

    # セキュリティ設定
    app.secret_key = os.getenv("SECRET_KEY", "default-development-key-change-in-production")
    app.config['SESSION_COOKIE_SECURE'] = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Babel（多言語対応）設定
    app.config['BABEL_DEFAULT_LOCALE'] = 'ja'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
    app.config['LANGUAGES'] = SUPPORTED_LANGUAGES

    # Babel初期化
    _babel = Babel(app)
    _babel.init_app(app, locale_selector=get_locale)

    # SocketIO初期化
    _socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

    return _socketio, _babel


def get_socketio():
    """SocketIOインスタンスを取得"""
    return _socketio


def get_babel():
    """Babelインスタンスを取得"""
    return _babel


# 認証設定
def get_admin_username():
    """管理者ユーザー名を取得"""
    return os.getenv("ADMIN_USERNAME", "admin")


def is_auth_required():
    """認証が必要かどうかを取得"""
    return os.getenv("REQUIRE_AUTH", "true").lower() == "true"
