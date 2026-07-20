"""
iso_utc（api/serializers.py）のテスト。

DBのDateTime列はnaive（UTCの壁時計値）で、従来は素のisoformat()を返して
いたためフロントの new Date() がローカル時刻と誤解釈し全時刻がTZ分ズレていた。
iso_utc は datetime に "Z" を付けてUTCを明示し、date（時刻なし）は据え置く。
"""

from datetime import datetime, date, timezone, timedelta

from api.serializers import iso_utc


class TestIsoUtc:
    def test_naive_datetime_gets_z(self):
        assert iso_utc(datetime(2026, 7, 20, 10, 0, 0)) == "2026-07-20T10:00:00Z"

    def test_naive_datetime_with_microseconds(self):
        assert iso_utc(datetime(2026, 7, 20, 10, 0, 0, 123456)) == \
            "2026-07-20T10:00:00.123456Z"

    def test_aware_datetime_converted_to_utc(self):
        jst = timezone(timedelta(hours=9))
        # 19:00 JST == 10:00 UTC
        assert iso_utc(datetime(2026, 7, 20, 19, 0, 0, tzinfo=jst)) == \
            "2026-07-20T10:00:00Z"

    def test_date_has_no_z(self):
        # date型は時刻・tzの概念がないためZを付けない
        assert iso_utc(date(2026, 7, 20)) == "2026-07-20"

    def test_none_returns_none(self):
        assert iso_utc(None) is None
