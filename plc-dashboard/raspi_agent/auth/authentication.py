"""
認証・パスワード管理

Phase 6セキュリティ修正 + Phase 7リファクタリング

このモジュールは以下を提供します:
- 安全なパスワードハッシュ（PBKDF2）
- 後方互換性のあるパスワード検証（SHA256サポート）
- 認証デコレータ
- 初期パスワード生成
"""

import os
import hashlib
import secrets
from functools import wraps

from flask import session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# 認証設定
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"


def _is_legacy_sha256_hash(hash_value):
    """SHA256ハッシュかどうかを判定（後方互換性用）

    SHA256は64文字の16進数文字列
    """
    return (hash_value and
            len(hash_value) == 64 and
            all(c in '0123456789abcdef' for c in hash_value.lower()))


def _legacy_hash_password(password):
    """旧方式のSHA256ハッシュ（後方互換性用）"""
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password):
    """パスワードをハッシュ化（werkzeugのPBKDF2を使用）

    Phase 6セキュリティ修正:
    - 旧方式: SHA256（saltなし、レインボーテーブル攻撃に脆弱）
    - 新方式: PBKDF2-SHA256（salt付き、計算コスト調整可能）

    Args:
        password: 平文パスワード

    Returns:
        str: ハッシュ化されたパスワード
    """
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)


def verify_password(password, password_hash):
    """パスワードを検証（新旧両方式に対応）

    Phase 6セキュリティ修正:
    - 新方式（werkzeug）と旧方式（SHA256）の両方に対応
    - 後方互換性を維持しつつ、セキュリティを向上

    Args:
        password: 検証する平文パスワード
        password_hash: 保存されているハッシュ値

    Returns:
        bool: パスワードが一致すればTrue
    """
    if _is_legacy_sha256_hash(password_hash):
        # 旧方式（SHA256）との互換性
        return _legacy_hash_password(password) == password_hash
    else:
        # 新方式（werkzeug PBKDF2）
        return check_password_hash(password_hash, password)


def get_current_admin_password_hash():
    """現在の管理者パスワードハッシュを取得（ローカル設定優先）

    優先順位:
    1. ローカル設定（ConfigManager）
    2. 環境変数
    3. None（初期設定を強制）

    Returns:
        str or None: パスワードハッシュ、未設定の場合はNone
    """
    from db_utils import ConfigManager

    config_manager = ConfigManager()
    local_hash = config_manager.get_admin_password_hash()

    if local_hash:
        return local_hash

    # 環境変数からハッシュを取得
    env_hash = os.getenv("ADMIN_PASSWORD_HASH")
    if env_hash:
        return env_hash

    # デフォルトパスワードは使用しない（初回セットアップを強制）
    return None


def generate_initial_password():
    """初期パスワードを生成（8文字のランダム文字列）

    Returns:
        str: 8文字のURL安全なランダム文字列
    """
    return secrets.token_urlsafe(6)[:8]


def require_auth(f):
    """認証が必要な機能のデコレータ

    REQUIRE_AUTHがFalseの場合は認証をスキップします。

    使用例:
        @app.route("/protected")
        @require_auth
        def protected_page():
            return "Protected content"
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not REQUIRE_AUTH:
            return f(*args, **kwargs)

        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def save_admin_password(new_password):
    """管理者パスワードを保存

    Args:
        new_password: 新しい平文パスワード

    Returns:
        bool: 保存成功時True
    """
    from db_utils import ConfigManager

    config_manager = ConfigManager()
    password_hash = hash_password(new_password)
    return config_manager.save_admin_password(password_hash)
