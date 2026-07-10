"""
クリーンアップ統合テスト（Phase 3）

3系統（CLI・管理API・スケジューラ）のクリーンアップを
scheduler.batch_cleanup に一本化したことの検証。

- batch_cleanup / cleanup_old_logs が保持日数より古いログのみ削除する
- retention_days の上書きが効く（既定はDATA_RETENTION_CONFIG=30日）
- 管理API /api/admin/cleanup がdays基準の件数を返す（count/削除の基準一致）
"""

import json
import threading
from datetime import datetime, timedelta, timezone

from db import db
from db.models import Log, DailyLogSummary
from api.scheduler import (
    batch_cleanup,
    cleanup_old_logs,
    cleanup_old_daily_summaries,
    DATA_RETENTION_CONFIG,
)


def _add_log(equipment_pk, age_days):
    """age_days日前のタイムスタンプでログを1件作成"""
    log = Log()
    log.equipment_id = equipment_pk
    log.timestamp = datetime.now(timezone.utc) - timedelta(days=age_days)
    log.temperature = 25.0
    db.session.add(log)
    return log


def _add_daily_summary(equipment_pk, age_days):
    """age_days日前の日付で日次集計を1件作成"""
    summary = DailyLogSummary(
        equipment_id=equipment_pk,
        date=(datetime.now(timezone.utc) - timedelta(days=age_days)).date(),
        data_count=1,
    )
    db.session.add(summary)
    return summary


class TestSchedulerCleanup:
    def test_default_retention_is_30_days(self):
        """SPEC §5.2: 生データ保持期間は30日"""
        assert DATA_RETENTION_CONFIG["raw_data_days"] == 30

    def test_deletes_only_older_than_retention(self, session, sample_equipment):
        """保持日数より古いログだけ削除し、新しいログは残す"""
        _add_log(sample_equipment.id, age_days=40)  # 削除対象
        _add_log(sample_equipment.id, age_days=35)  # 削除対象
        _add_log(sample_equipment.id, age_days=10)  # 保持
        _add_log(sample_equipment.id, age_days=1)  # 保持
        session.commit()

        deleted = cleanup_old_logs()  # 既定30日

        assert deleted == 2
        assert Log.query.count() == 2

    def test_retention_override(self, session, sample_equipment):
        """retention_days の上書きが効く"""
        _add_log(sample_equipment.id, age_days=20)  # 7日基準では削除対象
        _add_log(sample_equipment.id, age_days=5)  # 保持
        session.commit()

        deleted = cleanup_old_logs(retention_days=7)

        assert deleted == 1
        assert Log.query.count() == 1

    def test_no_target_returns_zero(self, session, sample_equipment):
        """削除対象が無ければ0件"""
        _add_log(sample_equipment.id, age_days=5)
        session.commit()

        assert cleanup_old_logs() == 0
        assert Log.query.count() == 1

    def test_batch_cleanup_spans_multiple_batches(self, session, sample_equipment):
        """バッチサイズを跨いでも全件削除される（境界の取りこぼしが無い）"""
        for _ in range(5):
            _add_log(sample_equipment.id, age_days=40)
        session.commit()

        deleted = batch_cleanup(
            model=Log,
            date_column=Log.timestamp,
            retention_days=30,
            data_name="ログ",
            batch_size=2,  # 5件を2件ずつ = 3バッチ
        )

        assert deleted == 5
        assert Log.query.count() == 0

    def test_batch_cleanup_explicit_cutoff_date(self, session, sample_equipment):
        """cutoff_date明示指定が優先され、retention_daysのnow基準計算に依存しない"""
        _add_log(sample_equipment.id, age_days=10)  # 保持
        _add_log(sample_equipment.id, age_days=3)  # 5日前cutoffなら保持
        session.commit()

        # retention_days=1（本来3日前も削除対象）だが、cutoffを5日前で固定 →
        # 明示cutoffが優先され、5日より古い1件のみ削除される
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        deleted = batch_cleanup(
            model=Log,
            date_column=Log.timestamp,
            retention_days=1,
            data_name="ログ",
            cutoff_date=cutoff,
        )

        assert deleted == 1
        assert Log.query.count() == 1


class TestDailySummaryCleanup:
    def test_daily_retention_is_365_days(self):
        """日次集計の保持期間は365日"""
        assert DATA_RETENTION_CONFIG["daily_data_days"] == 365

    def test_deletes_only_older_than_retention(self, session, sample_equipment):
        """365日より古い日次集計だけ削除し、新しいものは残す"""
        _add_daily_summary(sample_equipment.id, age_days=400)  # 削除対象
        _add_daily_summary(sample_equipment.id, age_days=366)  # 削除対象
        _add_daily_summary(sample_equipment.id, age_days=100)  # 保持
        _add_daily_summary(sample_equipment.id, age_days=1)  # 保持
        session.commit()

        deleted = cleanup_old_daily_summaries()

        assert deleted == 2
        assert DailyLogSummary.query.count() == 2

    def test_no_target_returns_zero(self, session, sample_equipment):
        """削除対象が無ければ0件"""
        _add_daily_summary(sample_equipment.id, age_days=30)
        session.commit()

        assert cleanup_old_daily_summaries() == 0
        assert DailyLogSummary.query.count() == 1


class TestAdminCleanupEndpoint:
    def test_cleanup_count_uses_request_days(self, client, session, sample_equipment):
        """管理APIの見積り件数がリクエストのdays基準（count/削除の基準一致）"""
        _add_log(sample_equipment.id, age_days=20)  # days=15なら対象
        _add_log(sample_equipment.id, age_days=5)  # 保持
        session.commit()

        resp = client.post(
            "/api/admin/cleanup",
            data=json.dumps({"days": 15}),
            content_type="application/json",
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["estimated_count"] == 1

    def test_cleanup_no_target(self, client, session, sample_equipment):
        """削除対象が無ければ0件で即応答"""
        _add_log(sample_equipment.id, age_days=5)
        session.commit()

        resp = client.post(
            "/api/admin/cleanup",
            data=json.dumps({"days": 30}),
            content_type="application/json",
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["deleted_count"] == 0

    def test_cleanup_passes_days_to_delete(
        self, client, session, sample_equipment, monkeypatch
    ):
        """削除本体 cleanup_old_logs に retention_days=days が渡る（配線の回帰検知）。

        バックグラウンドスレッドの実削除は非決定的なので、削除関数を差し替えて
        「daysが削除側にも貫通する」ことを同期的に検証する。旧実装は削除側が
        設定値raw_data_daysを使い、リクエストのdaysを無視するバグがあった。
        """
        import api.routes.admin as admin_module

        called = {}
        done = threading.Event()

        def fake_cleanup(retention_days=None):
            called["retention_days"] = retention_days
            done.set()
            return 0

        monkeypatch.setattr(admin_module, "cleanup_old_logs", fake_cleanup)

        _add_log(sample_equipment.id, age_days=40)  # 対象を1件作り分岐を通す
        session.commit()

        resp = client.post(
            "/api/admin/cleanup",
            data=json.dumps({"days": 15}),
            content_type="application/json",
        )
        assert resp.status_code == 200

        assert done.wait(timeout=5), "バックグラウンド削除が呼ばれなかった"
        assert called["retention_days"] == 15

    def test_cleanup_requires_admin(self, operator_client, session, sample_equipment):
        """operatorロールは403"""
        resp = operator_client.post(
            "/api/admin/cleanup",
            data=json.dumps({"days": 30}),
            content_type="application/json",
        )
        assert resp.status_code == 403
