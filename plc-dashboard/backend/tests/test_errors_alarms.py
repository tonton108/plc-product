"""
エラー・アラームAPI（api/routes/errors_alarms.py）のテスト

Phase 2-7 のエラーログ/アラーム/PLC状態エンドポイントを検証する。
従来このモジュールはカバレッジ22%と最低水準だったため、正常系＋主要な
異常系（404/400）を網羅してCIの回帰防御を厚くする（SPEC Phase 5・カバレッジ向上）。

全テストはインメモリSQLite（conftest.py）。client フィクスチャは
admin Bearer と エージェントAPIキーの両方を付与するため、require_user /
require_api_key のどちらのエンドポイントも叩ける。
"""
from datetime import datetime, timezone

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

    def test_save_error_log_wrong_content_type_returns_400(self, client, sample_equipment):
        """Content-Type不正/非JSONボディでも500ではなく400（get_json silent=True）"""
        resp = client.post(
            f"/api/equipment/{EQ}/error_logs",
            data="error_type=timeout",  # JSONではない
            content_type="text/plain",
        )
        assert resp.status_code == 400

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

    def test_save_error_log_creates_plc_status_when_absent(self, client, sample_equipment):
        """PLC状態が未作成でもエラーPOSTでレコードを新規作成し計上する。

        従来はPLCStatusの作成経路が本番に無くテーブルが常に空で、エラー計上が
        `if plc_status:` で握り潰されていた（連続エラー数が一度も記録されなかった）。
        """
        assert PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first() is None

        resp = client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": ErrorTypes.CONNECTION_FAILED, "error_message": "x",
        })
        assert resp.status_code == 200

        created = PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first()
        assert created is not None
        assert created.consecutive_errors == 1
        assert created.is_online is False
        assert created.last_error_type == ErrorTypes.CONNECTION_FAILED
        # 初期状態オフラインからの遷移ではないため状態変更時刻は据え置き（None）
        assert created.last_status_change_at is None

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


class TestPLCStatusRecovery:
    """データPOST成功時のPLC通信状態の回復（logs.save_log_data）。

    従来はエラー時に is_online=False / consecutive_errors++ する一方、成功時に
    戻す経路が本番コードに一切なく、一度でも通信エラーが起きた設備は復旧後も
    永久にオフライン表示・エラー数累積のままだった（last_communication_at も
    常にNULL）。
    """

    def _post_log(self, client, extra=None):
        payload = {"equipment_id": EQ, "temperature": 25.0}
        if extra:
            payload.update(extra)
        return client.post("/api/logs", json=payload)

    def test_log_post_creates_plc_status_when_absent(self, client, sample_equipment):
        """PLC状態が未作成でもデータPOST成功でオンライン状態のレコードを新規作成する。

        従来はPLCStatusの作成経路が本番に無く、回復ブロックが `if plc_status:` で
        常にスキップされ、通信状態が一度も永続化されなかった。
        """
        assert PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first() is None

        resp = self._post_log(client)
        assert resp.status_code == 200

        created = PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first()
        assert created is not None
        assert created.is_online is True
        assert created.consecutive_errors == 0
        assert created.last_communication_at is not None
        # 初期状態オフライン→オンラインの遷移として状態変更時刻が記録される
        assert created.last_status_change_at is not None

    def test_log_post_recovers_offline_status(self, client, session, sample_equipment):
        """オフライン・エラー累積中の設備がデータPOST成功でオンラインに回復する"""
        old_change = datetime(2020, 1, 1, tzinfo=timezone.utc)
        status = PLCStatus(equipment_id=sample_equipment.id)
        status.is_online = False
        status.consecutive_errors = 5
        status.last_status_change_at = old_change
        session.add(status)
        session.commit()

        resp = self._post_log(client)
        assert resp.status_code == 200

        refreshed = PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first()
        assert refreshed.is_online is True
        assert refreshed.consecutive_errors == 0
        assert refreshed.last_communication_at is not None
        # オフライン→オンラインの遷移なので状態変更時刻が更新される
        assert refreshed.last_status_change_at is not None
        assert refreshed.last_status_change_at.replace(tzinfo=timezone.utc) > old_change

    def test_log_post_when_already_online_keeps_change_time(
        self, client, session, sample_equipment
    ):
        """既にオンラインなら状態変更時刻は据え置き、通信時刻のみ更新される"""
        t0 = datetime(2021, 6, 1, tzinfo=timezone.utc)
        status = PLCStatus(equipment_id=sample_equipment.id)
        status.is_online = True
        status.consecutive_errors = 0
        status.last_status_change_at = t0
        session.add(status)
        session.commit()

        resp = self._post_log(client)
        assert resp.status_code == 200

        refreshed = PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first()
        assert refreshed.is_online is True
        assert refreshed.last_communication_at is not None
        # 遷移していないので状態変更時刻は変わらない
        assert refreshed.last_status_change_at.replace(tzinfo=timezone.utc) == t0

    def test_second_error_does_not_bump_change_time(
        self, client, session, sample_equipment
    ):
        """既にオフラインの設備への追加エラーでは状態変更時刻を更新しない"""
        status = PLCStatus(equipment_id=sample_equipment.id)
        status.is_online = True
        status.consecutive_errors = 0
        session.add(status)
        session.commit()

        # 1回目: オンライン→オフラインの遷移で状態変更時刻が入る
        client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": ErrorTypes.CONNECTION_FAILED, "error_message": "x",
        })
        first = PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first()
        assert first.is_online is False
        change_after_first = first.last_status_change_at
        assert change_after_first is not None

        # 2回目: 既にオフラインなので状態変更時刻は据え置き、エラー数のみ増える
        client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": ErrorTypes.CONNECTION_FAILED, "error_message": "y",
        })
        second = PLCStatus.query.filter_by(equipment_id=sample_equipment.id).first()
        assert second.consecutive_errors == 2
        assert second.last_status_change_at == change_after_first
