"""
ローカルバッファ機能のテストスクリプト（シンプル版）
"""

import os
import sys
import time
from datetime import datetime

# 環境変数を設定（テスト用）
os.environ["CENTRAL_SERVER_IP"] = "192.168.1.10"
os.environ["CENTRAL_SERVER_PORT"] = "5000"

from local_buffer import LocalBuffer
from db_utils import DatabaseAPI


def print_separator(title=""):
    """セパレータを表示"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)
    else:
        print("=" * 70)


def test_basic_operations():
    """基本操作のテスト"""
    print_separator("[TEST 1] 基本操作（保存・取得・削除）")

    # テスト用バッファを作成
    buffer = LocalBuffer(db_path="test_buffer.db", max_retry=3)

    # 1. データ保存
    print("\n[STEP 1] データをバッファに保存")
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "data_points": {"temperature": 25.5, "pressure": 1013.25, "humidity": 60.0},
    }

    record_id = buffer.save("TEST_001", test_data)
    print(f"  OK: 保存完了 (レコードID={record_id})")

    # 2. 未送信データ取得
    print("\n[STEP 2] 未送信データを取得")
    pending = buffer.get_pending(limit=10)
    print(f"  OK: 取得完了 ({len(pending)}件)")

    for rec_id, equipment_id, data in pending:
        print(f"    - ID={rec_id}, 設備={equipment_id}")
        print(f"      温度={data['data_points']['temperature']}度")

    # 3. 統計情報表示
    print("\n[STEP 3] バッファ統計")
    stats = buffer.get_stats()
    print(f"  総件数: {stats['total_count']}件")
    print(f"  設備別: {stats['equipment_stats']}")

    # 4. データ削除
    print("\n[STEP 4] データを削除")
    if pending:
        buffer.mark_as_sent(pending[0][0])
        print(f"  OK: 削除完了 (ID={pending[0][0]})")

    # 5. 削除後の統計
    print("\n[STEP 5] 削除後の統計")
    stats = buffer.get_stats()
    print(f"  総件数: {stats['total_count']}件")

    buffer.close()
    print("\n[TEST 1] 完了\n")


def test_server_down_simulation():
    """サーバーダウンのシミュレーション"""
    print_separator("[TEST 2] サーバーダウン時のシミュレーション")

    db_api = DatabaseAPI()

    # シナリオ説明
    print("\n[シナリオ]")
    print("  1. 中央サーバーがダウン（接続エラー）")
    print("  2. データはローカルバッファに保存される")
    print("  3. サーバー復旧時に自動再送信")

    # テストデータを5件作成
    print("\n[STEP 1] 5件のデータを送信試行")
    print("  ※サーバーに接続できないため、すべてバッファに保存されます")

    for i in range(5):
        test_data = {"temperature": 20.0 + i, "pressure": 1000.0 + i * 5, "count": i}

        equipment_id = f"TEST_{i+1:03d}"

        # 送信試行（失敗してバッファに保存される）
        success = db_api.send_log_data(equipment_id, test_data)

        if success:
            print(f"  OK: {equipment_id} サーバーに送信成功")
        else:
            print(f"  WARN: {equipment_id} 送信失敗 -> バッファに保存")

        time.sleep(0.3)

    # バッファの状態を確認
    print("\n[STEP 2] 現在のバッファ状態")
    stats = db_api.get_buffer_stats()

    # 未送信データの確認
    print("\n[STEP 3] 未送信データの確認")
    pending = db_api.buffer.get_pending(limit=100)
    print(f"  未送信データ: {len(pending)}件")

    if len(pending) > 0:
        print("\n  詳細（最初の3件）:")
        for rec_id, equipment_id, data in pending[:3]:
            print(
                f"    - ID={rec_id}, 設備={equipment_id}, 温度={data.get('temperature', 'N/A')}度"
            )

    # 再送信シミュレーション
    print("\n[STEP 4] 再送信を試行")
    print("  ※サーバーがダウンしているため、再送信は失敗します")
    success, failure, total = db_api.retry_pending_data(batch_size=10)
    print(f"  結果: 成功={success}, 失敗={failure}, 総数={total}")

    print("\n[TEST 2] 完了\n")


def test_retry_logic():
    """再試行ロジックのテスト"""
    print_separator("[TEST 3] 再試行ロジック")

    buffer = LocalBuffer(db_path="test_buffer_retry.db", max_retry=3)

    print("\n[STEP 1] テストデータを保存")
    test_data = {"value": 100}
    record_id = buffer.save("RETRY_TEST", test_data)
    print(f"  OK: 保存完了 (ID={record_id})")

    print("\n[STEP 2] 再試行カウントを増やす（失敗をシミュレート）")
    for i in range(4):
        buffer.increment_retry(record_id, f"テストエラー {i+1}回目")
        print(f"  試行 {i+1}回目: retry_count={i+1}")

    print("\n[STEP 3] 未送信データを取得（再送回数では除外しない）")
    pending = buffer.get_pending(limit=10)
    print(f"  取得されたデータ: {len(pending)}件")

    if len(pending) > 0:
        print("  OK: 正しく動作（上限超過でも再送対象であり続ける・日数で期限切れ）")

    print("\n[STEP 4] 日数ベースのクリーンアップ（本日データは残る）")
    deleted = buffer.cleanup_old_data(days=7)
    print(f"  削除されたデータ: {deleted}件（本日データのため0件）")

    buffer.close()
    print("\n[TEST 3] 完了\n")


def cleanup_test_files():
    """テストファイルを削除"""
    import os

    test_files = ["test_buffer.db", "test_buffer_retry.db"]

    print("\n[CLEANUP] テストファイルをクリーンアップ中...")
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"  削除: {file}")


def main():
    """メイン関数"""
    print_separator("ローカルバッファ機能 統合テスト")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # テスト1: 基本操作
        test_basic_operations()
        time.sleep(0.5)

        # テスト2: サーバーダウンシミュレーション
        test_server_down_simulation()
        time.sleep(0.5)

        # テスト3: 再試行ロジック
        test_retry_logic()

        print_separator("全テスト完了")
        print("[SUCCESS] すべてのテストが正常に完了しました")

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # クリーンアップ
        cleanup_test_files()
        print(f"\n終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
