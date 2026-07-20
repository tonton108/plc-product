"""
ローカルバッファ機能のテストスクリプト

このスクリプトは、中央サーバーがダウンしている状態を
シミュレートして、バッファリング機能の動作を確認します。
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
    print_separator("テスト1: 基本操作（保存・取得・削除）")

    # テスト用バッファを作成
    buffer = LocalBuffer(db_path="test_buffer.db", max_retry=3)

    # 1. データ保存
    print("\n📝 ステップ1: データをバッファに保存")
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "data_points": {"temperature": 25.5, "pressure": 1013.25, "humidity": 60.0},
    }

    record_id = buffer.save("TEST_001", test_data)
    print(f"  ✅ 保存完了: レコードID={record_id}")

    # 2. 未送信データ取得
    print("\n📋 ステップ2: 未送信データを取得")
    pending = buffer.get_pending(limit=10)
    print(f"  ✅ 取得完了: {len(pending)}件")

    for rec_id, equipment_id, data in pending:
        print(f"    - ID={rec_id}, 設備={equipment_id}")
        print(f"      データ: {data['data_points']}")

    # 3. 統計情報表示
    print("\n📊 ステップ3: バッファ統計")
    buffer.print_stats()

    # 4. データ削除
    print("\n🗑️ ステップ4: データを削除")
    if pending:
        buffer.mark_as_sent(pending[0][0])
        print(f"  ✅ 削除完了: ID={pending[0][0]}")

    # 5. 削除後の統計
    print("\n📊 ステップ5: 削除後の統計")
    buffer.print_stats()

    buffer.close()
    print("\n✅ 基本操作テスト完了")


def test_server_down_simulation():
    """サーバーダウンのシミュレーション"""
    print_separator("テスト2: サーバーダウン時のシミュレーション")

    db_api = DatabaseAPI()

    # シナリオ説明
    print("\n📖 シナリオ:")
    print("  1. 中央サーバーがダウン（接続エラー）")
    print("  2. データはローカルバッファに保存される")
    print("  3. サーバー復旧時に自動再送信")

    # テストデータを5件作成
    print("\n📝 ステップ1: 5件のデータを送信試行（サーバーダウン想定）")
    print("  ※実際にはサーバーに接続できないため、すべてバッファに保存されます")

    for i in range(5):
        test_data = {"temperature": 20.0 + i, "pressure": 1000.0 + i * 5, "count": i}

        equipment_id = f"TEST_{i+1:03d}"

        # 送信試行（失敗してバッファに保存される）
        success = db_api.send_log_data(equipment_id, test_data)

        if success:
            print(f"  ✅ {equipment_id}: サーバーに送信成功")
        else:
            print(f"  ⚠️ {equipment_id}: 送信失敗 → バッファに保存")

        time.sleep(0.5)

    # バッファの状態を確認
    print("\n📊 ステップ2: 現在のバッファ状態")
    stats = db_api.get_buffer_stats()

    # 未送信データの確認
    print("\n📋 ステップ3: 未送信データの確認")
    pending = db_api.buffer.get_pending(limit=100)
    print(f"  未送信データ: {len(pending)}件")

    if len(pending) > 0:
        print("\n  詳細:")
        for rec_id, equipment_id, data in pending[:3]:  # 最初の3件のみ表示
            print(f"    - ID={rec_id}, 設備={equipment_id}")

    # 再送信シミュレーション（実際にはサーバーが起動していないので失敗）
    print("\n🔄 ステップ4: 再送信を試行")
    print("  ※サーバーがダウンしているため、再送信は失敗します")
    success, failure, total = db_api.retry_pending_data(batch_size=10)

    # クリーンアップテスト
    print("\n🗑️ ステップ5: クリーンアップテスト（7日以上前のデータ削除）")
    deleted = db_api.cleanup_buffer(days=7)
    print(f"  削除されたデータ: {deleted}件（現在は新しいデータのため0件）")

    print("\n✅ サーバーダウンシミュレーション完了")


def test_retry_logic():
    """再試行ロジックのテスト"""
    print_separator("テスト3: 再試行ロジック")

    buffer = LocalBuffer(db_path="test_buffer_retry.db", max_retry=3)

    print("\n📝 ステップ1: テストデータを保存")
    test_data = {"value": 100}
    record_id = buffer.save("RETRY_TEST", test_data)
    print(f"  ✅ 保存完了: ID={record_id}")

    print("\n🔄 ステップ2: 再試行カウントを増やす（失敗をシミュレート）")
    for i in range(4):
        buffer.increment_retry(record_id, f"テストエラー {i+1}回目")
        print(f"  試行 {i+1}回目: retry_count={i+1}")

    print("\n📋 ステップ3: 未送信データを取得（再送回数では除外しない）")
    pending = buffer.get_pending(limit=10)
    print(f"  取得されたデータ: {len(pending)}件")

    if len(pending) > 0:
        print("  ✅ 正しく動作: 上限超過でも再送対象であり続ける（日数で期限切れ）")

    print("\n🗑️ ステップ4: 日数ベースのクリーンアップ（本日データは残る）")
    deleted = buffer.cleanup_old_data(days=7)
    print(f"  削除されたデータ: {deleted}件（本日データのため0件）")

    buffer.close()
    print("\n✅ 再試行ロジックテスト完了")


def cleanup_test_files():
    """テストファイルを削除"""
    import os

    test_files = ["test_buffer.db", "test_buffer_retry.db"]

    print("\n🧹 テストファイルをクリーンアップ中...")
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
        time.sleep(1)

        # テスト2: サーバーダウンシミュレーション
        test_server_down_simulation()
        time.sleep(1)

        # テスト3: 再試行ロジック
        test_retry_logic()

        print_separator("全テスト完了")
        print("✅ すべてのテストが正常に完了しました")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # クリーンアップ
        cleanup_test_files()
        print(f"\n終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
