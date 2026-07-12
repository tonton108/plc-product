"""
集計ロジック（api/scheduler.py の create_daily_summary / create_monthly_summary）のテスト

Issue #10 で共通化された日次→月次の集計本体を検証する。固定項目
（current/temperature/pressure/cycle_time）と動的項目（Log.data）の
avg/max/min、生産数（累積の最大）、エラー件数、稼働日数、冪等性を確認する。

インメモリSQLite（conftest.py）。テストは session フィクスチャの app_context 内で
実行されるため、集計関数を直接呼べる。
"""
from datetime import date, datetime, timezone

from db import db
from db.models import Log, DailyLogSummary, MonthlyLogSummary
from api.scheduler import create_daily_summary, create_monthly_summary

DAY = date(2026, 6, 15)


def _log(eq_id, hour, **kw):
    return Log(equipment_id=eq_id, timestamp=datetime(2026, 6, 15, hour, 0, 0), **kw)


class TestCreateDailySummary:
    def test_aggregates_fixed_and_dynamic(self, session, sample_equipment):
        """固定項目のavg/max/min・生産数・エラー数・動的項目集計が正しい"""
        eq = sample_equipment.id
        session.add_all([
            _log(eq, 8, current=10, temperature=100, pressure=1.0, cycle_time=5,
                 production_count=100, error_code=0, data={"sensor_x": 40}),
            _log(eq, 10, current=20, temperature=110, pressure=2.0, cycle_time=7,
                 production_count=150, error_code=1, data={"sensor_x": 50}),
            _log(eq, 12, current=30, temperature=120, pressure=3.0, cycle_time=9,
                 production_count=200, error_code=5, data={"sensor_x": 60}),
        ])
        session.commit()

        create_daily_summary(DAY)

        s = DailyLogSummary.query.filter_by(equipment_id=eq, date=DAY).first()
        assert s is not None
        assert s.data_count == 3
        assert s.current_avg == 20 and s.current_max == 30 and s.current_min == 10
        assert s.temperature_avg == 110 and s.temperature_max == 120 and s.temperature_min == 100
        assert s.pressure_avg == 2.0 and s.pressure_max == 3.0 and s.pressure_min == 1.0
        assert s.cycle_time_avg == 7
        # 生産数は累積値の最大、エラーは error_code>0 の件数
        assert s.production_count_total == 200
        assert s.error_count == 2
        # 動的項目
        assert s.data_summary["sensor_x_avg"] == 50
        assert s.data_summary["sensor_x_max"] == 60
        assert s.data_summary["sensor_x_min"] == 40

    def test_excludes_logs_outside_target_date(self, session, sample_equipment):
        """対象日外のログは集計に含めない"""
        eq = sample_equipment.id
        session.add_all([
            _log(eq, 9, current=10),
            Log(equipment_id=eq, timestamp=datetime(2026, 6, 16, 9), current=999),  # 翌日
        ])
        session.commit()

        create_daily_summary(DAY)

        s = DailyLogSummary.query.filter_by(equipment_id=eq, date=DAY).first()
        assert s.data_count == 1
        assert s.current_avg == 10

    def test_idempotent_rerun_replaces(self, session, sample_equipment):
        """同じ日を再集計しても重複せず上書きされる"""
        eq = sample_equipment.id
        session.add(_log(eq, 9, current=10))
        session.commit()
        create_daily_summary(DAY)
        # 値を変えて再集計
        session.add(_log(eq, 11, current=30))
        session.commit()
        create_daily_summary(DAY)

        rows = DailyLogSummary.query.filter_by(equipment_id=eq, date=DAY).all()
        assert len(rows) == 1
        assert rows[0].data_count == 2
        assert rows[0].current_avg == 20  # (10+30)/2

    def test_no_logs_creates_no_summary(self, session, sample_equipment):
        """設備はあるがログが無ければ集計は作られない"""
        create_daily_summary(DAY)
        assert DailyLogSummary.query.count() == 0

    def test_no_equipment_returns_early(self, session):
        """設備未登録なら早期リターン（例外を投げない）"""
        create_daily_summary(DAY)
        assert DailyLogSummary.query.count() == 0


class TestCreateMonthlySummary:
    def _daily(self, eq_id, day, **kw):
        return DailyLogSummary(equipment_id=eq_id, date=date(2026, 6, day), **kw)

    def test_aggregates_daily_into_monthly(self, session, sample_equipment):
        """日次集計を月次に集約: avg=日次avgの平均, max=maxの最大, 生産=totalの最大, error=合計"""
        eq = sample_equipment.id
        session.add_all([
            self._daily(eq, 1, production_count_total=200,
                        current_avg=10, current_max=15, current_min=5,
                        temperature_avg=100, temperature_max=105, temperature_min=95,
                        error_count=2, data_count=10,
                        data_summary={"sensor_x_avg": 40, "sensor_x_max": 50, "sensor_x_min": 30}),
            self._daily(eq, 2, production_count_total=250,
                        current_avg=20, current_max=25, current_min=8,
                        temperature_avg=110, temperature_max=115, temperature_min=90,
                        error_count=3, data_count=10,
                        data_summary={"sensor_x_avg": 44, "sensor_x_max": 52, "sensor_x_min": 33}),
        ])
        session.commit()

        create_monthly_summary(2026, 6)

        m = MonthlyLogSummary.query.filter_by(equipment_id=eq, year=2026, month=6).first()
        assert m is not None
        assert m.current_avg == 15          # (10+20)/2
        assert m.current_max == 25          # max(15,25)
        assert m.current_min == 5           # min(5,8)
        assert m.temperature_avg == 105     # (100+110)/2
        assert m.production_count_total == 250   # max(200,250)
        assert m.error_count_total == 5     # 2+3
        assert m.operational_days == 2
        # 動的項目の月次集約
        assert m.data_summary["sensor_x_avg"] == 42   # (40+44)/2
        assert m.data_summary["sensor_x_max"] == 52
        assert m.data_summary["sensor_x_min"] == 30

    def test_idempotent_rerun_replaces(self, session, sample_equipment):
        """同じ年月を再集計しても重複しない"""
        eq = sample_equipment.id
        session.add(self._daily(eq, 1, current_avg=10, current_max=10, current_min=10,
                                error_count=0, data_count=1))
        session.commit()
        create_monthly_summary(2026, 6)
        create_monthly_summary(2026, 6)

        rows = MonthlyLogSummary.query.filter_by(equipment_id=eq, year=2026, month=6).all()
        assert len(rows) == 1

    def test_no_daily_creates_no_monthly(self, session, sample_equipment):
        """対象月の日次集計が無ければ月次は作られない"""
        create_monthly_summary(2026, 6)
        assert MonthlyLogSummary.query.count() == 0
