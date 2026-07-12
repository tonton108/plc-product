"""
履歴API get_history_data_optimized（GET /api/logs/<id>/history_optimized）のテスト

Issue #14 の中核となる期間別エンドポイント。短期間(1h/6h/24h)は生ログ
（data_source=raw_logs）、長期間(7d/30d)は日次集計（data_source=daily_summaries）を
返す分岐と、期間バリデーション(400)・設備404を検証する。既存テストは
latest/history/POST を覆っていたが、このエンドポイントは未カバーだった。

インメモリSQLite（conftest.py）。client は admin 認証付き。
"""
from datetime import datetime, timedelta, timezone

from db.models import Log, DailyLogSummary

EQ = "TEST_001"


def _recent_log(eq_id, minutes_ago=5, **kw):
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return Log(equipment_id=eq_id, timestamp=ts, **kw)


class TestHistoryOptimized:
    def test_short_period_returns_raw_logs(self, client, session, sample_equipment):
        """1h: data_source=raw_logs、直近ログが含まれる"""
        session.add(_recent_log(sample_equipment.id, minutes_ago=5, current=42))
        session.commit()

        resp = client.get(f"/api/logs/{EQ}/history_optimized?period=1h")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data_source"] == "raw_logs"
        assert body["period"] == "1h"
        assert body["total_records"] == 1
        assert body["data"][0]["current"] == 42

    def test_short_period_excludes_older_than_window(self, client, session, sample_equipment):
        """1h: ウィンドウ外(2時間前)の生ログは含まれない"""
        session.add(_recent_log(sample_equipment.id, minutes_ago=120, current=1))
        session.commit()

        resp = client.get(f"/api/logs/{EQ}/history_optimized?period=1h")
        assert resp.status_code == 200
        assert resp.get_json()["total_records"] == 0

    def test_long_period_returns_daily_summaries(self, client, session, sample_equipment):
        """7d: data_source=daily_summaries、期間内の日次集計を返す"""
        today = datetime.now(timezone.utc).date()
        session.add(DailyLogSummary(
            equipment_id=sample_equipment.id, date=today,
            data_count=10, current_avg=25.0,
            data_summary={"sensor_x_avg": 42.5}))
        session.commit()

        resp = client.get(f"/api/logs/{EQ}/history_optimized?period=7d")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data_source"] == "daily_summaries"
        assert body["total_records"] == 1
        # 日次集計は date キーを持つ（Issue #14 の参照キー切替の根拠）
        assert body["data"][0]["date"] == str(today)

    def test_long_period_excludes_older_summaries(self, client, session, sample_equipment):
        """30d: 期間外(40日前)の日次集計は含まれない"""
        old = (datetime.now(timezone.utc) - timedelta(days=40)).date()
        session.add(DailyLogSummary(
            equipment_id=sample_equipment.id, date=old, data_count=1))
        session.commit()

        resp = client.get(f"/api/logs/{EQ}/history_optimized?period=30d")
        assert resp.status_code == 200
        assert resp.get_json()["total_records"] == 0

    def test_default_period_is_1h_raw(self, client, session, sample_equipment):
        """period 省略時は 1h（raw_logs）"""
        resp = client.get(f"/api/logs/{EQ}/history_optimized")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["period"] == "1h"
        assert body["data_source"] == "raw_logs"

    def test_invalid_period_returns_400(self, client, sample_equipment):
        """未対応の期間は400"""
        resp = client.get(f"/api/logs/{EQ}/history_optimized?period=99y")
        assert resp.status_code == 400
        assert "Invalid period" in resp.get_json()["error"]

    def test_equipment_not_found_returns_404(self, client):
        """存在しない設備は404"""
        resp = client.get("/api/logs/NOPE/history_optimized?period=1h")
        assert resp.status_code == 404
