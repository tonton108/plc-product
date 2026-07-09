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


# last_used_at の更新間隔（秒）。棚卸し用途なので秒単位の精度は不要。
# 毎リクエストUPDATEすると200台が共有キー1本を使う運用（SPEC.md §4.2）で
# 同一行への行ロック競合がボトルネックになるため、間隔を空けて更新する
LAST_USED_UPDATE_INTERVAL_SEC = 300


def authenticate_api_key(raw_key):
    """APIキーを検証し、有効ならAgentApiKeyを返す（無効ならNone）"""
    if not raw_key:
        return None

    api_key = AgentApiKey.query.filter_by(key_hash=hash_token(raw_key)).first()
    if api_key is None or not api_key.is_active:
        return None

    # 使用時刻を記録（失効判断・棚卸しに使う）。更新は間隔を空け、
    # 失敗しても認証自体は成立させる（記録は本質でないため）
    now = datetime.now(timezone.utc)
    last_used = api_key.last_used_at
    if last_used is not None and last_used.tzinfo is None:
        last_used = last_used.replace(tzinfo=timezone.utc)
    if last_used is None or (now - last_used).total_seconds() >= LAST_USED_UPDATE_INTERVAL_SEC:
        try:
            api_key.last_used_at = now
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning(f"APIキーのlast_used_at更新に失敗しました（認証は続行）: {e}")
    return api_key


def extract_bearer_token():
    """AuthorizationヘッダからBearerトークンを取り出す"""
    header = request.headers.get(AUTH_HEADER, "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip()
    return None


def _authenticate_request_user():
    """リクエストのBearerトークンからユーザーを解決し g.current_user に格納"""
    user = authenticate_token(extract_bearer_token())
    if user is not None:
        g.current_user = user
    return user


def _request_equipment_identifier(view_kwargs):
    """リクエストが対象とする設備ID（文字列）を特定する

    URLパラメータ（/api/equipment/<equipment_id>/...）を優先し、
    無ければJSONボディの equipment_id（POST /api/logs, /api/register）を見る。
    どちらにも無ければ None（設備を特定しないリクエスト）。
    """
    if 'equipment_id' in view_kwargs:
        return view_kwargs['equipment_id']
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data.get('equipment_id')
    return None


def _api_key_in_scope(api_key, view_kwargs):
    """設備別APIキーのスコープ検証（SPEC.md §4.2）

    - equipment_id が NULL のキー（全設備共有キー）: 常に許可
    - 設備別キー: リクエスト対象の設備がキーに紐付く設備と一致する場合のみ許可。
      対象設備を特定できないリクエスト（一覧検索等）は許可する
    """
    if api_key.equipment_id is None:
        return True

    equipment_id_str = _request_equipment_identifier(view_kwargs)
    if not equipment_id_str:
        # 設備を特定しないリクエストはスコープ判定の対象外
        return True

    from db.models import Equipment
    equipment = Equipment.query.filter_by(equipment_id=equipment_id_str).first()
    # 未登録設備への操作（新規登録含む）は設備別キーでは不可（共有キーで行う）
    return equipment is not None and equipment.id == api_key.equipment_id


def _authenticate_request_api_key(view_kwargs=None):
    """リクエストのX-API-KeyからAPIキーを解決し g.api_key に格納

    設備別キーの場合はリクエスト対象設備とのスコープ一致も検証する。
    """
    api_key = authenticate_api_key(request.headers.get(API_KEY_HEADER))
    if api_key is None:
        return None
    if not _api_key_in_scope(api_key, view_kwargs or {}):
        logger.warning(
            f"APIキーのスコープ外アクセスを拒否: key={api_key.name} "
            f"(equipment_id={api_key.equipment_id})"
        )
        return None
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
    """有効なエージェントAPIキーを要求するデコレータ（設備別キーはスコープも検証）"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        api_key = _authenticate_request_api_key(kwargs)
        if api_key is None:
            return jsonify({"error": "有効なAPIキーが必要です"}), 401
        return f(*args, **kwargs)
    return wrapper


def require_user_or_api_key(role=None):
    """ユーザートークンまたはAPIキーのどちらかを要求するデコレータ

    フロントエンド（人間）とエージェント（ラズパイ）の両方が使う
    エンドポイント用。APIキーで認証された場合、roleチェックは行わない
    （設備別キーの場合はスコープ検証が代わりに効く）。

    Args:
        role: ユーザートークンで認証された場合に要求するロール
              （Noneならログイン済みであればよい）
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if _authenticate_request_api_key(kwargs) is not None:
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
