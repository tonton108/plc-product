"""
認証サービスモジュール（Phase 1）

Bearerトークン（ユーザー認証）とAPIキー（エージェント認証）の検証、
およびルート保護用デコレータを提供します。

使い分け（SPEC.md §4）:
- require_user()                  : ログイン済みユーザーなら誰でも（閲覧系）
- require_user(role="admin")      : adminロールのみ（設備設定変更・管理操作）
- require_api_key                 : エージェント専用（/api/logs 等）
- require_user_or_api_key(...)    : フロントとエージェント両方が使うエンドポイント
"""

import logging
from datetime import datetime, timezone
from functools import wraps

from flask import g, jsonify, request

from db import db
from db.models import AgentApiKey, AuthToken, User, UserRoles
from db.models.auth import hash_token

logger = logging.getLogger(__name__)

# HTTPヘッダ名
AUTH_HEADER = "Authorization"
API_KEY_HEADER = "X-API-Key"


# === 検証本体 ===

def authenticate_token(raw_token):
    """Bearerトークンを検証し、有効ならUserを返す（無効ならNone）"""
    if not raw_token:
        return None

    token = AuthToken.query.filter_by(token_hash=hash_token(raw_token)).first()
    if token is None:
        return None

    if token.is_expired():
        # 期限切れトークンはその場で削除（テーブル肥大防止）
        db.session.delete(token)
        db.session.commit()
        return None

    user = User.query.get(token.user_id)
    if user is None or not user.is_active:
        return None

    return user


def authenticate_api_key(raw_key):
    """APIキーを検証し、有効ならAgentApiKeyを返す（無効ならNone）"""
    if not raw_key:
        return None

    api_key = AgentApiKey.query.filter_by(key_hash=hash_token(raw_key)).first()
    if api_key is None or not api_key.is_active:
        return None

    # 使用時刻を記録（失効判断・棚卸しに使う）
    api_key.last_used_at = datetime.now(timezone.utc)
    db.session.commit()
    return api_key


def _extract_bearer_token():
    """AuthorizationヘッダからBearerトークンを取り出す"""
    header = request.headers.get(AUTH_HEADER, "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip()
    return None


def _authenticate_request_user():
    """リクエストのBearerトークンからユーザーを解決し g.current_user に格納"""
    user = authenticate_token(_extract_bearer_token())
    if user is not None:
        g.current_user = user
    return user


def _authenticate_request_api_key():
    """リクエストのX-API-KeyからAPIキーを解決し g.api_key に格納"""
    api_key = authenticate_api_key(request.headers.get(API_KEY_HEADER))
    if api_key is not None:
        g.api_key = api_key
    return api_key


# === デコレータ ===

def require_user(role=None):
    """ログイン済みユーザーを要求するデコレータ

    Args:
        role: 指定した場合、そのロールのみ許可（例: UserRoles.ADMIN）
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = _authenticate_request_user()
            if user is None:
                return jsonify({"error": "認証が必要です"}), 401
            if role is not None and user.role != role:
                return jsonify({"error": "この操作を行う権限がありません"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_api_key(f):
    """有効なエージェントAPIキーを要求するデコレータ"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        api_key = _authenticate_request_api_key()
        if api_key is None:
            return jsonify({"error": "有効なAPIキーが必要です"}), 401
        return f(*args, **kwargs)
    return wrapper


def require_user_or_api_key(role=None):
    """ユーザートークンまたはAPIキーのどちらかを要求するデコレータ

    フロントエンド（人間）とエージェント（ラズパイ）の両方が使う
    エンドポイント用。APIキーで認証された場合、roleチェックは行わない。

    Args:
        role: ユーザートークンで認証された場合に要求するロール
              （Noneならログイン済みであればよい）
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if _authenticate_request_api_key() is not None:
                return f(*args, **kwargs)

            user = _authenticate_request_user()
            if user is None:
                return jsonify({"error": "認証が必要です"}), 401
            if role is not None and user.role != role:
                return jsonify({"error": "この操作を行う権限がありません"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# === Socket.IO用 ===

def authenticate_socketio_connect(auth):
    """Socket.IO接続ハンドシェイクの認証

    Args:
        auth: クライアントが io(url, { auth: { token } }) で渡したdict

    Returns:
        User（認証成功）または None（拒否すべき）
    """
    raw_token = None
    if isinstance(auth, dict):
        raw_token = auth.get("token")
    return authenticate_token(raw_token)
