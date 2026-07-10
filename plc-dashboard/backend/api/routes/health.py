"""
ヘルスチェックAPI

アプリケーションの正常性確認エンドポイントを提供します。
唯一の無認証エンドポイント（死活監視・CI起動待ち用）。
"""

import os

from flask import Blueprint, jsonify
from sqlalchemy import text

from db import db

health_bp = Blueprint("health", __name__, url_prefix="/api")


def _check_message_queue():
    """message_queue(Redis)の疎通を確認する。

    ingest分離構成（Phase 4）では、ingest側のemitはRedis経由でviewer側の
    クライアントへ届く。Redisが落ちると配信が壊れる（かつingestのemitは
    握り潰される）ため、SOCKETIO_MESSAGE_QUEUEが設定されている場合は
    その疎通も死活監視の対象にする。未設定（単一プロセス）ならチェックしない。

    Returns:
        str | None: "connected" / "disconnected"、未設定なら None
    """
    mq = os.getenv("SOCKETIO_MESSAGE_QUEUE")
    if not mq or not mq.startswith("redis"):
        return None
    try:
        import redis

        client = redis.Redis.from_url(mq, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return "connected"
    except Exception:
        return "disconnected"


@health_bp.route("/health", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント

    DB疎通を確認し（プロセス起動だけでなく「使える状態」を保証）、
    ingest分離構成ではmessage_queue(Redis)の疎通も確認する。
    いずれかが不通なら503を返す（NSSMの自動再起動・プロキシのヘルスチェック用）。
    CIの起動待ちはこの200を条件にしている。

    レスポンスは後方互換のため `status`/`database` を維持しつつ、
    運用向けに `role`（ingest/viewer/single）と `message_queue` を追加。
    """
    healthy = True

    try:
        db.session.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "disconnected"
        healthy = False

    message_queue = _check_message_queue()
    if message_queue == "disconnected":
        healthy = False

    body = {
        "status": "healthy" if healthy else "unhealthy",
        "role": os.getenv("ROLE", "single"),
        "database": database,
    }
    if message_queue is not None:
        body["message_queue"] = message_queue

    return jsonify(body), (200 if healthy else 503)
