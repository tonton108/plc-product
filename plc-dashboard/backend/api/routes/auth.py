"""
認証APIルート（Phase 1）

- POST /api/auth/login  : ログイン（トークン発行）
- POST /api/auth/logout : ログアウト（トークン失効）
- GET  /api/auth/me     : ログイン中ユーザー情報
"""

import logging

from flask import Blueprint, g, jsonify, request

from db import db
from db.models import AuthToken, User
from db.models.auth import hash_token
from api.auth_service import require_user, _extract_bearer_token

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """ログイン。成功時はBearerトークンとユーザー情報を返す"""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "ユーザー名とパスワードを入力してください"}), 400

    user = User.query.filter_by(username=username).first()

    # ユーザー不存在と誤パスワードは同じ応答にする（ユーザー名の存在を漏らさない）
    if user is None or not user.check_password(password) or not user.is_active:
        logger.warning(f"ログイン失敗: username={username}")
        return jsonify({"error": "ユーザー名またはパスワードが正しくありません"}), 401

    # 期限切れトークンをこのタイミングで掃除（テーブル肥大防止）
    for token in user.tokens:
        if token.is_expired():
            db.session.delete(token)

    token, raw_token = AuthToken.issue(user)
    db.session.add(token)
    db.session.commit()

    logger.info(f"ログイン成功: username={username} role={user.role}")
    return jsonify({
        "token": raw_token,
        "user": user.to_dict(),
    })


@auth_bp.route('/logout', methods=['POST'])
@require_user()
def logout():
    """ログアウト。使用中のトークンを失効させる"""
    raw_token = _extract_bearer_token()
    token = AuthToken.query.filter_by(token_hash=hash_token(raw_token)).first()
    if token is not None:
        db.session.delete(token)
        db.session.commit()
    return jsonify({"message": "ログアウトしました"})


@auth_bp.route('/me', methods=['GET'])
@require_user()
def me():
    """ログイン中のユーザー情報を返す（フロントの起動時セッション確認用）"""
    return jsonify({"user": g.current_user.to_dict()})
