"""
ヘルスチェック（/api/health）のテスト（Phase 4）

DB疎通に加え、ingest分離構成でのmessage_queue(Redis)疎通・役割報告を検証する。
"""


class TestHealthCheck:
    def test_healthy_without_message_queue(self, unauth_client, monkeypatch):
        """message_queue未設定なら200・database connected・message_queueフィールド無し"""
        monkeypatch.delenv("SOCKETIO_MESSAGE_QUEUE", raising=False)
        monkeypatch.delenv("ROLE", raising=False)

        resp = unauth_client.get("/api/health")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "healthy"
        assert body["database"] == "connected"
        assert body["role"] == "single"
        assert "message_queue" not in body

    def test_reports_role(self, unauth_client, monkeypatch):
        """ROLE環境変数が応答に反映される（ingest/viewerの識別）"""
        monkeypatch.setenv("ROLE", "ingest")
        resp = unauth_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.get_json()["role"] == "ingest"

    def test_unhealthy_when_redis_down(self, unauth_client, monkeypatch):
        """message_queue設定済みでRedisが不通なら503・message_queue disconnected"""
        # 未使用ポートで確実に接続失敗させる
        monkeypatch.setenv("SOCKETIO_MESSAGE_QUEUE", "redis://127.0.0.1:6399/0")

        resp = unauth_client.get("/api/health")
        assert resp.status_code == 503
        body = resp.get_json()
        assert body["status"] == "unhealthy"
        assert body["message_queue"] == "disconnected"
        # DBは生きているのでdatabaseはconnectedのまま
        assert body["database"] == "connected"
