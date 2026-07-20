"""
ローカルバッファの保持ポリシー回帰テスト

未配信データが「再送回数」ではなく「経過日数」でのみ破棄されることを検証する。
旧実装では retry_count が max_retry に達したデータが、
- get_pending から除外され（再送されなくなる）
- cleanup_max_retry_exceeded で配信成否・経過日数を問わず削除される
ため、約10分（retry_interval 60秒 × max_retry 10回）を超える障害で未配信
データが恒久欠損していた。この回帰を防ぐ。
"""

import os
import sys
import json
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_buffer import LocalBuffer


@pytest.fixture
def buffer(tmp_path):
    """一時ファイル上のバッファ（max_retry=3 で上限到達を作りやすくする）"""
    db_path = str(tmp_path / "retention_test.db")
    buf = LocalBuffer(db_path=db_path, max_retry=3)
    yield buf
    buf.close()


class TestRetentionByAge:
    def test_pending_returned_after_exceeding_max_retry(self, buffer):
        """retry_count が max_retry を超えても get_pending は返し続ける"""
        record_id = buffer.save("EQ_1", {"value": 42})

        # max_retry(3) を超える 5 回失敗させる
        for _ in range(5):
            buffer.increment_retry(record_id, "サーバー到達不可")

        pending = buffer.get_pending(limit=10)
        assert len(pending) == 1, "上限超過でも再送対象であり続けるべき"
        assert pending[0][0] == record_id

    def test_cleanup_buffer_keeps_recent_undelivered_data(self, buffer):
        """日数ベースのクリーンアップは新しい未配信データを削除しない"""
        record_id = buffer.save("EQ_1", {"value": 42})
        for _ in range(5):
            buffer.increment_retry(record_id, "サーバー到達不可")

        # 日数ベースのクリーンアップ（cleanup_old_data）は今日のデータを消さない
        deleted = buffer.cleanup_old_data(days=7)
        assert deleted == 0
        assert (
            len(buffer.get_pending(limit=10)) == 1
        ), "未配信データが恒久欠損してはならない"

    def test_cleanup_old_data_removes_aged_records(self, buffer):
        """経過日数を超えたデータは（未配信でも）削除される"""
        record_id = buffer.save("EQ_1", {"value": 42})

        # created_at を8日前に書き換える（保存期間7日を超過させる）
        old_ts = datetime.now() - timedelta(days=8)
        with buffer._lock:
            buffer.conn.execute(
                "UPDATE pending_data SET created_at = ? WHERE id = ?",
                (old_ts, record_id),
            )
            buffer.conn.commit()

        deleted = buffer.cleanup_old_data(days=7)
        assert deleted == 1
        assert len(buffer.get_pending(limit=10)) == 0

    def test_successful_send_still_deletes(self, buffer):
        """送信成功時は従来どおり mark_as_sent で削除される"""
        record_id = buffer.save("EQ_1", {"value": 42})
        buffer.mark_as_sent(record_id)
        assert len(buffer.get_pending(limit=10)) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
