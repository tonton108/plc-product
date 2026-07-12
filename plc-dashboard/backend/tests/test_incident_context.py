"""
インシデント文脈保全（SPEC §5.2）のテスト

エラー/アラーム発生時に、該当設備の発生前ウィンドウの生ログを incident_context へ
退避し、生ログ本体が消えても後から追える（インシデント追跡）ことを検証する。

インメモリSQLite（conftest.py）。client は admin Bearer + APIキー付き。
"""
from datetime import datetime, timedelta, timezone

from db import db
from db.models import Log, IncidentContext, CommunicationErrorLog
from api.scheduler import (
    cleanup_old_logs,
    cleanup_old_incident_context,
    backfill_incident_aftermath,
)

EQ = "TEST_001"


def _log(eq_id, minutes_ago, **kw):
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return Log(equipment_id=eq_id, timestamp=ts, **kw)


class TestCaptureOnError:
    def test_error_captures_leadup_logs(self, client, session, sample_equipment):
        """POST error_log で、発生前5分以内の生ログがincident_contextに保全される"""
        session.add_all([
            _log(sample_equipment.id, 2, current=10),   # ウィンドウ内
            _log(sample_equipment.id, 4, current=20),   # ウィンドウ内
            _log(sample_equipment.id, 30, current=99),  # ウィンドウ外(5分超)
        ])
        session.commit()

        resp = client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": "TIMEOUT", "error_message": "x",
            "plc_ip": "192.168.1.100", "protocol": "MC",
        })
        assert resp.status_code == 200

        ctx = IncidentContext.query.filter_by(equipment_id=sample_equipment.id).all()
        assert len(ctx) == 1
        inc = ctx[0]
        assert inc.event_type == "error"
        # 発生前5分以内の2件のみ（30分前は除外）
        assert inc.log_count == 2
        assert {row["current"] for row in inc.context_data} == {10, 20}
        # event_ref_id は作成されたエラーログを指す
        assert CommunicationErrorLog.query.get(inc.event_ref_id) is not None

    def test_error_with_no_recent_logs_captures_empty(self, client, session, sample_equipment):
        """直近ログが無くてもエラー記録は成功し、空の文脈が残る"""
        resp = client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": "TIMEOUT", "error_message": "x",
            "plc_ip": "192.168.1.100", "protocol": "MC",
        })
        assert resp.status_code == 200
        inc = IncidentContext.query.filter_by(equipment_id=sample_equipment.id).first()
        assert inc is not None and inc.log_count == 0


class TestCaptureFailureIsIsolated:
    def test_error_log_survives_when_capture_fails(
        self, client, session, sample_equipment, monkeypatch
    ):
        """文脈保全のINSERTが失敗しても、エラー記録本体は残る（best-effort保証）。

        capture内はSAVEPOINTで囲まれており、失敗しても外側のトランザクション
        （エラーログ本体）を巻き込まないことを検証する。JSON化不能な値を
        仕込んでflushを失敗させる。
        """
        import api.routes.errors_alarms as ea

        # context_dataにJSON化できない値(set)を混入させ、flush時に失敗させる
        monkeypatch.setattr(
            ea.LogSerializer, "to_list", staticmethod(lambda logs: [{"bad": {1, 2, 3}}])
        )

        resp = client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": "TIMEOUT", "error_message": "x",
            "plc_ip": "192.168.1.100", "protocol": "MC",
        })
        # エラー記録自体は成功する
        assert resp.status_code == 200
        # エラーログ本体は残る
        assert CommunicationErrorLog.query.filter_by(
            equipment_id=sample_equipment.id).count() == 1
        # 文脈は保全されない（巻き戻された）
        assert IncidentContext.query.filter_by(
            equipment_id=sample_equipment.id).count() == 0


class TestCaptureOnAlarm:
    def test_alarm_captures_context(self, client, session, sample_equipment):
        """POST alarm でも文脈が保全される"""
        session.add(_log(sample_equipment.id, 1, temperature=130))
        session.commit()

        resp = client.post(f"/api/equipment/{EQ}/alarms", json={
            "alarm_code": "E-101", "alarm_level": "WARNING", "alarm_message": "温度異常",
        })
        assert resp.status_code == 200
        inc = IncidentContext.query.filter_by(
            equipment_id=sample_equipment.id, event_type="alarm").first()
        assert inc is not None
        assert inc.log_count == 1
        assert inc.context_data[0]["temperature"] == 130


class TestSurvivesRawCleanup:
    def test_context_survives_after_raw_logs_deleted(self, client, session, sample_equipment):
        """生ログがクリーンアップで消えても、incident_contextは残り追跡できる"""
        session.add(_log(sample_equipment.id, 1, current=42))
        session.commit()
        client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": "TIMEOUT", "plc_ip": "1", "protocol": "MC",
        })
        # 生ログを全消去（保持0日相当を模擬: 全logを古く見せる）
        for log in Log.query.all():
            log.timestamp = datetime.now(timezone.utc) - timedelta(days=60)
        session.commit()
        cleanup_old_logs(retention_days=30)  # 30日より前を削除

        assert Log.query.count() == 0                     # 生ログは消えた
        inc = IncidentContext.query.first()
        assert inc is not None and inc.log_count == 1     # 文脈は残る
        assert inc.context_data[0]["current"] == 42       # 生の値も残る


def _incident(eq_id, event_minutes_ago, after_minutes):
    """テスト用にIncidentContextを直接作成する。

    event_time = now - event_minutes_ago、after_window_end = event_time + after_minutes。
    after_minutes を負にすれば after_window_end を過去（backfill対象）にできる。
    """
    now = datetime.now(timezone.utc)
    event_time = now - timedelta(minutes=event_minutes_ago)
    return IncidentContext(
        equipment_id=eq_id,
        event_type="error",
        event_ref_id=1,
        event_time=event_time,
        window_start=event_time - timedelta(minutes=5),
        window_end=event_time,
        context_data=[],
        log_count=0,
        after_window_end=event_time + timedelta(minutes=after_minutes),
    )


class TestAftermathBackfill:
    def test_capture_sets_pending_after_window(self, client, session, sample_equipment):
        """捕捉直後は after_window_end が設定され、after_captured_at は未設定（保留）"""
        resp = client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": "TIMEOUT", "plc_ip": "1", "protocol": "MC",
        })
        assert resp.status_code == 200
        inc = IncidentContext.query.filter_by(equipment_id=sample_equipment.id).first()
        assert inc.after_window_end is not None
        assert inc.after_captured_at is None       # 発生後はまだ未捕捉
        assert inc.after_log_count == 0

    def test_backfill_captures_post_event_logs(self, session, sample_equipment):
        """after_window_endを過ぎたインシデントの発生後ログのみが後追い保存される"""
        # 発生10分前、発生後ウィンドウ+5分（=5分前、過去なのでbackfill対象）
        inc = _incident(sample_equipment.id, event_minutes_ago=10, after_minutes=5)
        session.add(inc)
        # event_time は now-10分。発生後ウィンドウは (now-10) 〜 (now-5)
        session.add_all([
            _log(sample_equipment.id, 8, current=1),    # 発生後ウィンドウ内(now-8)
            _log(sample_equipment.id, 12, current=2),   # 発生前(now-12) → 除外
            _log(sample_equipment.id, 2, current=3),    # ウィンドウ後(now-2) → 除外
        ])
        session.commit()

        filled = backfill_incident_aftermath()
        assert filled == 1
        session.refresh(inc)
        assert inc.after_captured_at is not None
        assert inc.after_log_count == 1
        assert inc.after_context_data[0]["current"] == 1

        # 冪等: 再実行しても再捕捉しない
        assert backfill_incident_aftermath() == 0
        session.refresh(inc)
        assert inc.after_log_count == 1

    def test_backfill_skips_future_window(self, session, sample_equipment):
        """after_window_endが未来のインシデントはbackfillされない（保留のまま）"""
        inc = _incident(sample_equipment.id, event_minutes_ago=1, after_minutes=5)  # 未来
        session.add(inc)
        session.commit()

        assert backfill_incident_aftermath() == 0
        session.refresh(inc)
        assert inc.after_captured_at is None

    def test_legacy_row_without_after_window_is_ignored(
        self, client, session, sample_equipment
    ):
        """移行前の既存行(after_window_end=None)はbackfill対象外・APIで判別可能"""
        now = datetime.now(timezone.utc)
        legacy = IncidentContext(
            equipment_id=sample_equipment.id, event_type="error", event_ref_id=1,
            event_time=now, window_start=now, window_end=now,
            context_data=[], log_count=0,  # after_window_end 未指定=None
        )
        session.add(legacy)
        session.commit()

        assert backfill_incident_aftermath() == 0   # 対象外
        body = client.get(f"/api/equipment/{EQ}/incidents").get_json()
        assert body[0]["after_window_end"] is None
        assert body[0]["after_captured"] is False

    def test_retrieval_includes_aftermath(self, client, session, sample_equipment):
        """取得APIに発生後の捕捉状況・データが含まれる"""
        inc = _incident(sample_equipment.id, event_minutes_ago=10, after_minutes=5)
        session.add(inc)
        session.add(_log(sample_equipment.id, 8, current=42))
        session.commit()
        backfill_incident_aftermath()

        lst = client.get(f"/api/equipment/{EQ}/incidents").get_json()
        assert lst[0]["after_captured"] is True
        assert lst[0]["after_log_count"] == 1

        detail = client.get(
            f"/api/equipment/{EQ}/incidents/{inc.id}/context").get_json()
        assert detail["after_context_data"][0]["current"] == 42


class TestCleanup:
    def test_old_incident_context_deleted(self, session, sample_equipment):
        """保持期間(1年)を過ぎたincident_contextは削除、期間内は保持"""
        now = datetime.now(timezone.utc)
        old = IncidentContext(equipment_id=sample_equipment.id, event_type="error",
                              event_ref_id=1, event_time=now, window_start=now,
                              window_end=now, context_data=[], log_count=0)
        old.created_at = now - timedelta(days=400)   # 1年超
        recent = IncidentContext(equipment_id=sample_equipment.id, event_type="error",
                                 event_ref_id=2, event_time=now, window_start=now,
                                 window_end=now, context_data=[], log_count=0)
        recent.created_at = now - timedelta(days=10)
        session.add_all([old, recent])
        session.commit()

        deleted = cleanup_old_incident_context()
        assert deleted == 1
        remaining = IncidentContext.query.all()
        assert len(remaining) == 1 and remaining[0].event_ref_id == 2


class TestRetrievalAPI:
    def test_list_and_get_context(self, client, session, sample_equipment):
        """一覧APIは軽量、詳細APIはcontext_dataを含む"""
        session.add(_log(sample_equipment.id, 1, current=7))
        session.commit()
        client.post(f"/api/equipment/{EQ}/error_logs", json={
            "error_type": "TIMEOUT", "plc_ip": "1", "protocol": "MC",
        })

        lst = client.get(f"/api/equipment/{EQ}/incidents")
        assert lst.status_code == 200
        body = lst.get_json()
        assert len(body) == 1
        assert "context_data" not in body[0]          # 一覧は軽量
        inc_id = body[0]["id"]

        detail = client.get(f"/api/equipment/{EQ}/incidents/{inc_id}/context")
        assert detail.status_code == 200
        d = detail.get_json()
        assert d["context_data"][0]["current"] == 7   # 詳細は生データ含む

    def test_get_context_not_found(self, client, sample_equipment):
        resp = client.get(f"/api/equipment/{EQ}/incidents/99999/context")
        assert resp.status_code == 404
