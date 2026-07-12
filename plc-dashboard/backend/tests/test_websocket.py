"""
WebSocketハンドラ（api/routes/websocket.py）のテスト

Phase 1 で必須化された Socket.IO ハンドシェイクのトークン認証を中心に検証する。
接続確立（on_connect）は無効/未指定トークンを拒否するセキュリティ要の経路。
Flask-SocketIO の test_client で接続可否を確認する。

インメモリSQLite（conftest.py）。socketio はモジュールグローバルで、
create_app（app フィクスチャ）がハンドラ登録＋init_app 済み。
"""
from app import socketio as sio


class TestSocketConnectAuth:
    def test_connect_with_valid_token_accepted(self, app, admin_token):
        """有効なBearerトークンを auth で渡すと接続が確立する"""
        client = sio.test_client(app, auth={'token': admin_token})
        assert client.is_connected() is True
        client.disconnect()

    def test_connect_with_invalid_token_rejected(self, app, admin_token):
        """無効なトークンは接続拒否（is_connected=False）"""
        client = sio.test_client(app, auth={'token': 'not-a-real-token'})
        assert client.is_connected() is False

    def test_connect_without_auth_rejected(self, app):
        """auth未指定は接続拒否"""
        client = sio.test_client(app)
        assert client.is_connected() is False

    def test_connect_with_empty_token_rejected(self, app):
        """空トークンは接続拒否"""
        client = sio.test_client(app, auth={'token': ''})
        assert client.is_connected() is False

    def test_operator_token_accepted(self, app, session):
        """operatorロールのトークンでも接続は確立する（閲覧は全ロール可）"""
        from db.models import User, AuthToken, UserRoles
        user = User(username='ws_operator', password='pw', role=UserRoles.OPERATOR)
        session.add(user)
        session.commit()
        token, raw = AuthToken.issue(user)
        session.add(token)
        session.commit()

        client = sio.test_client(app, auth={'token': raw})
        assert client.is_connected() is True
        client.disconnect()

    def test_join_and_leave_do_not_disconnect(self, app, admin_token, session, sample_equipment):
        """接続後に join/leave_monitoring を送っても接続が維持される（ハンドラが例外を出さない）"""
        client = sio.test_client(app, auth={'token': admin_token})
        assert client.is_connected() is True

        client.emit('join_monitoring', {'equipment_id': sample_equipment.equipment_id})
        client.emit('leave_monitoring', {'equipment_id': sample_equipment.equipment_id})
        # ハンドラ内で例外が出れば切断されるため、接続維持＝正常処理の確認になる
        assert client.is_connected() is True
        client.disconnect()

    def test_get_realtime_status_handler_runs(self, app, admin_token, session, sample_equipment):
        """get_realtime_status を送ってもハンドラが落ちず接続が維持される"""
        from db.models import Log
        from datetime import datetime, timezone
        session.add(Log(equipment_id=sample_equipment.id,
                        timestamp=datetime.now(timezone.utc), current=10))
        session.commit()

        client = sio.test_client(app, auth={'token': admin_token})
        client.emit('get_realtime_status', {'equipment_id': sample_equipment.equipment_id})
        assert client.is_connected() is True
        client.disconnect()
