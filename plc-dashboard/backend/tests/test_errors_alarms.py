"""
エラー・アラームAPI（api/routes/errors_alarms.py）のテスト

Phase 2-7 のエラーログ/アラーム/PLC状態エンドポイントを検証する。
従来このモジュールはカバレッジ22%と最低水準だったため、正常系＋主要な
異常系（404/400）を網羅してCIの回帰防御を厚くする（SPEC Phase 5・カバレッジ向上）。

全テストはインメモリSQLite（conftest.py）。client フィクスチャは
admin Bearer と エージェントAPIキーの両方を付与するため、require_user /
require_api_key のどちらのエンドポイントも叩ける。
"""
from db.models import CommunicationErrorLog, AlarmHistory, PLCStatus, ErrorTypes, AlarmLevels

EQ = "TEST_001"  # sample_equipment の equipment_id


class TestErrorLogs:
    def test_save_error_log_success(self, client, sample_equipment):
        """POST error_logs: 記録に成功し200、DBに1件保存される"""
        resp = client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": ErrorTypes.TIMEOUT,
            "error_message": "接続タイムアウト",
            "retry_count": 3,
            "plc_ip": "192.168.1.100",
            "protocol": "MC",
        })
        assert resp.status_code == 200
        logs = CommunicationErrorLog.query.filter_by(equipment_id=sample_equipment.id).all()
        assert len(logs) == 1
        assert logs[0].error_type == ErrorTypes.TIMEOUT
        assert logs[0].retry_count == 3

    def test_save_error_log_increments_plc_status(self, client, session, sample_equipment):
        """既存PLC状態があれば連続エラー数が増えオフラインになる"""
        status = PLCStatus(equipment_id=sample_equipment.id)
        status.consecutive_errors = 0
        status.is_online = True
        session.add(status)
        session.commit()

        client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": ErrorTypes.CONNECTION_FAILED, "error_message": "x",
            "plc_ip": "192.168.1.100", "protocol": "MC",
        })
        refreshed = PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first()
        assert refreshed.consecutive_errors == 1
        assert refreshed.is_online is False

    def test_save_error_log_equipment_not_found(self, client):
        """存在しない設備IDは404"""
        resp = client.post("/api/equipment/NOPE/error_logs", json={"error_type": ErrorTypes.UNKNOWN})
        assert resp.status_code == 404

    def test_save_error_log_no_data(self, client, sample_equipment):
        """空JSONは400（No JSON data provided）"""
        resp = client.post(f"/api/equipment/{EQ}/error_logs", json={})
        assert resp.status_code == 400

    def test_get_error_logs_success(self, client, sample_equipment):
        """GET error_logs: 記録後に一覧取得で200・件数一致"""
        client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": ErrorTypes.TIMEOUT, "error_message": "a",
            "plc_ip": "192.168.1.100", "protocol": "MC",
        })
        resp = client.get(f"/api/equipment/{EQ}/error_logs")
        assert resp.status_code == 200
        body = resp.get_json()
        assert isinstance(body, list) and len(body) == 1

    def test_get_error_logs_equipment_not_found(self, client):
        resp = client.get("/api/equipment/NOPE/error_logs")
        assert resp.status_code == 404

    def test_resolve_error_log_success(self, client, sample_equipment):
        """PATCH resolve: resolved_at が設定される"""
        client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": ErrorTypes.TIMEOUT, "error_message": "a",
            "plc_ip": "192.168.1.100", "protocol": "MC",
        })
        log = CommunicationErrorLog.query.filter_by(equipment_id=sample_equipment.id).first()
        assert log.resolved_at is None

        resp = client.patch(f"/api/equipment/{EQ}/error_logs/{log.id}/resolve")
        assert resp.status_code == 200
        assert resp.get_json()["error_log_id"] == log.id
        assert CommunicationErrorLog.query.get(log.id).resolved_at is not None

    def test_resolve_error_log_not_found(self, client, sample_equipment):
        """存在しないエラーログIDは404"""
        resp = client.patch(f"/api/equipment/{EQ}/error_logs/99999/resolve")
        assert resp.status_code == 404


class TestAlarms:
    def _post_alarm(self, client, level=AlarmLevels.WARNING):
        return client.post(f"/api/equipment/{EQ}/alarms", json={
            "alarm_code": "E-101",
            "alarm_level": level,
            "alarm_message": "温度異常",
            "alarm_data": {"temp": 130},
        })

    def test_save_alarm_success(self, client, sample_equipment):
        """POST alarms: 200・alarm_id を返し、DBに保存される"""
        resp = self._post_alarm(client)
        assert resp.status_code == 200
        alarm_id = resp.get_json()["alarm_id"]
        assert alarm_id is not None
        saved = AlarmHistory.query.get(alarm_id)
        assert saved.alarm_code == "E-101"
        assert saved.alarm_level == AlarmLevels.WARNING

    def test_save_alarm_equipment_not_found(self, client):
        resp = client.post("/api/equipment/NOPE/alarms", json={"alarm_code": "X"})
        assert resp.status_code == 404

    def test_save_alarm_no_data(self, client, sample_equipment):
        resp = client.post(f"/api/equipment/{EQ}/alarms", json={})
        assert resp.status_code == 400

    def test_get_alarms_success(self, client, sample_equipment):
        self._post_alarm(client)
        resp = client.get(f"/api/equipment/{EQ}/alarms")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    def test_get_alarms_equipment_not_found(self, client):
        resp = client.get("/api/equipment/NOPE/alarms")
        assert resp.status_code == 404

    def test_acknowledge_alarm_success(self, client, sample_equipment):
        """PATCH acknowledge: acknowledged=True・acknowledged_by 反映"""
        alarm_id = self._post_alarm(client).get_json()["alarm_id"]
        resp = client.patch(f"/api/equipment/{EQ}/alarms/{alarm_id}/acknowledge",
                            json={"acknowledged_by": "山田"})
        assert resp.status_code == 200
        assert resp.get_json()["acknowledged_by"] == "山田"
        saved = AlarmHistory.query.get(alarm_id)
        assert saved.acknowledged is True
        assert saved.acknowledged_by == "山田"
        assert saved.acknowledged_at is not None

    def test_acknowledge_alarm_default_by(self, client, sample_equipment):
        """acknowledged_by 省略時は System（空JSONを送るケース）"""
        alarm_id = self._post_alarm(client).get_json()["alarm_id"]
        resp = client.patch(f"/api/equipment/{EQ}/alarms/{alarm_id}/acknowledge", json={})
        assert resp.status_code == 200
        assert AlarmHistory.query.get(alarm_id).acknowledged_by == "System"

    def test_acknowledge_alarm_not_found(self, client, sample_equipment):
        resp = client.patch(f"/api/equipment/{EQ}/alarms/99999/acknowledge")
        assert resp.status_code == 404

    def test_clear_alarm_success(self, client, sample_equipment):
        """PATCH clear: cleared_at が設定される"""
        alarm_id = self._post_alarm(client).get_json()["alarm_id"]
        resp = client.patch(f"/api/equipment/{EQ}/alarms/{alarm_id}/clear")
        assert resp.status_code == 200
        assert AlarmHistory.query.get(alarm_id).cleared_at is not None

    def test_clear_alarm_not_found(self, client, sample_equipment):
        resp = client.patch(f"/api/equipment/{EQ}/alarms/99999/clear")
        assert resp.status_code == 404


class TestPLCStatus:
    def test_get_plc_status_success(self, client, session, sample_equipment):
        """PLC状態があれば200で返る"""
        status = PLCStatus(equipment_id=sample_equipment.id)
        status.is_online = True
        status.consecutive_errors = 2
        session.add(status)
        session.commit()

        resp = client.get(f"/api/equipment/{EQ}/plc_status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["consecutive_errors"] == 2

    def test_get_plc_status_never_reported_returns_default(self, client, sample_equipment):
        """設備はあるがPLC状態未作成なら、404ではなく200＋既定ステータス。

        「未報告」は正常系でありリソース不在ではない。兄弟API（alarms/error_logs）が
        空データで200を返すのと整合させる。never_reported=True で実報告と区別できる。
        """
        resp = client.get(f"/api/equipment/{EQ}/plc_status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["is_online"] is False
        assert body["consecutive_errors"] == 0
        assert body["never_reported"] is True
        assert body["equipment_id"] == EQ

    def test_get_plc_status_equipment_not_found(self, client):
        """設備自体が存在しない場合は依然404（未報告の正常系と区別される）"""
        resp = client.get("/api/equipment/NOPE/plc_status")
        assert resp.status_code == 404
