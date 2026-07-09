"""
認証モデルモジュール

User（ユーザー）、AuthToken（ログイントークン）、AgentApiKey（エージェントAPIキー）を定義します。

Phase 1（認証）: SPEC.md §4 に基づく新規実装
- ユーザー認証はBearerトークン方式（DB保存の不透明トークン。失効・無効化が即時反映できる）
- エージェント認証はAPIキー方式（equipment_id が NULL のキーは全設備共有キー）
- トークン・キーとも平文は保存せず SHA-256 ハッシュのみ保存する
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from db import db


# ユーザーロール定数
class UserRoles:
    ADMIN = "admin"        # 設備設定の変更、ユーザー管理、データ削除・クリーンアップ
    OPERATOR = "operator"  # 閲覧＋現場操作（アラーム確認・解除、エラー解決）

    @classmethod
    def get_all(cls):
        return [cls.ADMIN, cls.OPERATOR]


def hash_token(raw_token: str) -> str:
    """トークン/APIキーの保存用ハッシュを計算（SHA-256、平文は保存しない）"""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class User(db.Model):
    """ユーザーテーブル（admin / operator の2ロール）"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRoles.OPERATOR)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tokens = db.relationship('AuthToken', backref='user', lazy=True, cascade='all, delete-orphan')

    def __init__(self, username: str, password: str, role: str = UserRoles.OPERATOR, is_active: bool = True):
        if role not in UserRoles.get_all():
            raise ValueError(f"不正なロール: {role}（{UserRoles.get_all()} のいずれか）")
        self.username = username
        self.set_password(password)
        self.role = role
        self.is_active = is_active

    def set_password(self, password: str):
        """パスワードをPBKDF2でハッシュ化して保存"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """APIレスポンス用（password_hashは含めない）"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
        }


class AuthToken(db.Model):
    """ログイントークンテーブル（Bearerトークンのハッシュを保存）"""
    __tablename__ = 'auth_tokens'

    # トークン有効期間（時間）
    TOKEN_LIFETIME_HOURS = 24

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, user_id: int, token_hash: str, expires_at: datetime):
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = expires_at

    @classmethod
    def issue(cls, user: "User") -> tuple["AuthToken", str]:
        """新しいトークンを発行する。戻り値は (AuthTokenレコード, 平文トークン)。

        平文トークンはこの戻り値でのみ得られる（DBにはハッシュのみ保存）。
        """
        raw_token = secrets.token_urlsafe(32)
        token = cls(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=cls.TOKEN_LIFETIME_HOURS),
        )
        return token, raw_token

    def is_expired(self) -> bool:
        expires = self.expires_at
        # SQLite等はnaiveで返すためUTCとして比較する
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires < datetime.now(timezone.utc)


class AgentApiKey(db.Model):
    """エージェントAPIキーテーブル

    equipment_id が NULL のキーは全設備共有キー（SPEC.md §4.2:
    運用は共有キー1本で開始し、設備別キーへコード変更なしで移行できる設計）。
    """
    __tablename__ = 'agent_api_keys'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, name: str, key_hash: str, equipment_id: Optional[int] = None, is_active: bool = True):
        self.name = name
        self.key_hash = key_hash
        self.equipment_id = equipment_id
        self.is_active = is_active

    @classmethod
    def issue(cls, name: str, equipment_id: Optional[int] = None, raw_key: Optional[str] = None) -> tuple["AgentApiKey", str]:
        """新しいAPIキーを発行する。戻り値は (AgentApiKeyレコード, 平文キー)。

        raw_key を指定した場合はその値を使う（E2E/CI用のシードで既知の値を登録するため）。
        """
        if raw_key is None:
            raw_key = secrets.token_urlsafe(32)
        api_key = cls(name=name, key_hash=hash_token(raw_key), equipment_id=equipment_id)
        return api_key, raw_key
