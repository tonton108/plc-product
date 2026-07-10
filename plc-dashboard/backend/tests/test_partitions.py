"""
logsパーティション管理のテスト（Phase 3）

パーティションDDLはPostgres専用で、単体テストはSQLiteインメモリで走る。
そのため実際のパーティション挙動（pruning・ルーティング・DROP削除）は
実Postgresでの手動/統合検証に委ね、ここでは「SQLiteでは安全にno-opする」という
ガードの回帰のみを固定する（本番Postgres以外でDDLが暴発しないことの担保）。
"""

from datetime import date

from api.partitions import (
    ensure_log_partitions,
    logs_is_partitioned,
    drop_old_log_partitions,
    _add_months,
    _month_start,
)


class TestEnsureLogPartitionsGuard:
    def test_noop_on_sqlite(self, app):
        """SQLite（テスト環境）ではパーティション作成を行わず0を返す"""
        with app.app_context():
            assert ensure_log_partitions() == 0
            assert ensure_log_partitions(months_ahead=6) == 0


class TestPartitionCleanupGuard:
    def test_not_partitioned_on_sqlite(self, app):
        """SQLiteではlogsはパーティションでない（DROP最適化は使わない）"""
        with app.app_context():
            assert logs_is_partitioned() is False

    def test_drop_old_partitions_noop_on_sqlite(self, app):
        """SQLiteではパーティションDROPを行わず0を返す"""
        with app.app_context():
            assert drop_old_log_partitions(30) == 0


class TestMonthArithmetic:
    def test_month_start(self):
        assert _month_start(date(2026, 7, 15)) == date(2026, 7, 1)

    def test_add_months_within_year(self):
        assert _add_months(date(2026, 7, 1), 3) == date(2026, 10, 1)

    def test_add_months_year_rollover(self):
        assert _add_months(date(2026, 11, 1), 3) == date(2027, 2, 1)

    def test_add_months_december_boundary(self):
        assert _add_months(date(2026, 12, 1), 1) == date(2027, 1, 1)
