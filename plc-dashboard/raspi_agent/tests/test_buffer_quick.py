"""
ローカルバッファ機能のクイックテスト
"""

import os
import sys
from datetime import datetime

# 環境変数を設定（テスト用）
os.environ["CENTRAL_SERVER_IP"] = "192.168.1.10"
os.environ["CENTRAL_SERVER_PORT"] = "5000"

from local_buffer import LocalBuffer


def test_buffer_basic():
    """基本機能のテスト"""
    print("=" * 70)
    print("  ローカルバッファ機能 クイックテスト")
    print("=" * 70)

    # テスト用バッファを作成
    buffer = LocalBuffer(db_path="test_quick.db", max_retry=3)

    # 1. データ保存
    print("\n[TEST 1] データ保存")
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "temperature": 25.5,
        "pressure": 1013.25,
    }

    record_id = buffer.save("TEST_001", test_data)
    print(f"  OK: 保存成功 - レコードID={record_id}")

    # 2. 未送信データ取得
    print("\n[TEST 2] 未送信データ取得")
    pending = buffer.get_pending(limit=10)
    print(f"  OK: 取得成功 - {len(pending)}件")

    if pending:
        rec_id, equipment_id, data = pending[0]
        print(f"    - ID={rec_id}, 設備={equipment_id}")
        print(f"    - 温度={data['temperature']}度")

    # 3. 再試行カウント更新
    print("\n[TEST 3] 再試行カウント更新")
    if pending:
        buffer.increment_retry(pending[0][0], "テストエラー")
        print(f"  OK: 更新成功 - ID={pending[0][0]}")

    # 4. 統計情報
    print("\n[TEST 4] 統計情報")
    stats = buffer.get_stats()
    print(f"  総件数: {stats['total_count']}件")
    print(f"  設備別: {stats['equipment_stats']}")
    print(f"  再試行回数別: {stats['retry_stats']}")

    # 5. データ削除
    print("\n[TEST 5] データ削除")
    if pending:
        buffer.mark_as_sent(pending[0][0])
        print(f"  OK: 削除成功 - ID={pending[0][0]}")

    # 6. 削除後の統計
    print("\n[TEST 6] 削除後の統計")
    stats = buffer.get_stats()
    print(f"  総件数: {stats['total_count']}件")

    buffer.close()

    # クリーンアップ
    import os

    if os.path.exists("test_quick.db"):
        os.remove("test_quick.db")
        print("\n[CLEANUP] テストファイルを削除しました")

    print("\n" + "=" * 70)
    print("  [SUCCESS] すべてのテストが正常に完了しました")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_buffer_basic()
    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
