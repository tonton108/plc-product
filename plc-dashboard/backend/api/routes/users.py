"""
ユーザー管理API（admin専用）

トレイアプリのadmin画面（SPEC.md §3.1 / §4.1）向け。従来 `flask auth` CLI のみだった
ユーザー操作（一覧・作成・パスワード再設定・有効/無効化）をHTTPで提供する。
全操作 admin ロール必須。パスワードは平文を保存せず、発行/再設定時のみ平文を返す。
"""

import secrets

from flask import Blueprint, request, jsonify, g

from db import db
from db.models import User, UserRoles
from api.auth_service import require_user
from api.serializers import iso_utc

users_bp = Blueprint('admin_users', __name__, url_prefix='/api/admin/users')


def _generate_password() -> str:
    """初期/再設定パスワードを生成（cli.py の _generate_password と同一仕様: 12文字URL-safe）"""
    return secrets.token_urlsafe(9)


def _revoke_tokens(user: User) -> None:
    """ユーザーの既存ログイントークンを全失効（パスワード変更・無効化時の原則）"""
    for token in list(user.tokens):
        db.session.delete(token)


def _user_dict(user: User) -> dict:
    """管理画面用のユーザー表現（password_hashは含めない。created_atを付与）"""
    data = user.to_dict()
    data["created_at"] = iso_utc(user.created_at)
    return data


def _validate_optional_password(password):
    """passwordが指定されている場合は非空文字列であることを検証。問題があればエラー文言を返す。"""
    if password is not None and (not isinstance(password, str) or password == ''):
        return "passwordは空にできません"
    return None


@users_bp.route('', methods=['GET'])
@require_user(role=UserRoles.ADMIN)
def list_users():
    """ユーザー一覧を返す"""
    users = User.query.order_by(User.id).all()
    return jsonify({"users": [_user_dict(u) for u in users]}), 200


@users_bp.route('', methods=['POST'])
@require_user(role=UserRoles.ADMIN)
def create_user():
    """ユーザーを作成する。passwordを省略すると自動生成し、そのときだけ平文を返す。"""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    role = data.get('role') or UserRoles.OPERATOR
    password = data.get('password')

    if not username:
        return jsonify({"error": "usernameは必須です"}), 400
    if role not in UserRoles.get_all():
        return jsonify({"error": f"roleは {UserRoles.get_all()} のいずれかです"}), 400
    err = _validate_optional_password(password)
    if err:
        return jsonify({"error": err}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": f"ユーザー '{username}' は既に存在します"}), 409

    generated = password is None
    if generated:
        password = _generate_password()

    user = User(username=username, password=password, role=role)
    db.session.add(user)
    db.session.commit()

    resp = {"user": _user_dict(user)}
    if generated:
        # 発行時のみ平文を返す（DBにはハッシュのみ保存・再表示不可）
        resp["generated_password"] = password
    return jsonify(resp), 201


@users_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@require_user(role=UserRoles.ADMIN)
def reset_password(user_id):
    """パスワードを再設定する。省略時は自動生成して平文を返す。既存トークンは全失効。"""
    data = request.get_json() or {}
    password = data.get('password')
    err = _validate_optional_password(password)
    if err:
        return jsonify({"error": err}), 400

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "ユーザーが見つかりません"}), 404

    generated = password is None
    if generated:
        password = _generate_password()
    user.set_password(password)
    _revoke_tokens(user)
    db.session.commit()

    resp = {"user": _user_dict(user)}
    if generated:
        resp["generated_password"] = password
    return jsonify(resp), 200


@users_bp.route('/<int:user_id>/deactivate', methods=['POST'])
@require_user(role=UserRoles.ADMIN)
def deactivate_user(user_id):
    """ユーザーを無効化する（削除はしない）。自己ロックアウトと管理不能化を防ぐ。"""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "ユーザーが見つかりません"}), 404

    # 最後の有効なadminは無効化できない（ユーザー管理が不能になるため）。
    # 自己ガードより先に判定する（単独adminが自分を無効化しようとした場合も、
    # より本質的な「最後のadmin」理由を返す）。
    if user.role == UserRoles.ADMIN and user.is_active:
        active_admins = User.query.filter_by(role=UserRoles.ADMIN, is_active=True).count()
        if active_admins <= 1:
            return jsonify({"error": "最後の有効なadminは無効化できません"}), 400

    # 自分自身は無効化できない（自己ロックアウト防止）
    current = getattr(g, 'current_user', None)
    if current is not None and current.id == user.id:
        return jsonify({"error": "自分自身を無効化することはできません"}), 400

    user.is_active = False
    _revoke_tokens(user)
    db.session.commit()
    return jsonify({"user": _user_dict(user)}), 200


@users_bp.route('/<int:user_id>/activate', methods=['POST'])
@require_user(role=UserRoles.ADMIN)
def activate_user(user_id):
    """無効化したユーザーを再度有効化する"""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "ユーザーが見つかりません"}), 404

    user.is_active = True
    db.session.commit()
    return jsonify({"user": _user_dict(user)}), 200
