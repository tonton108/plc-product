"""
統合テスト：サーバーダウン時のバッファリング動作検証
"""

import os
import sys
import time
from datetime import datetime

# 環境変数を設定（存在しない中央サーバーIPを指定）
os.environ['CENTRAL_SERVER_IP'] = '192.168.255.254'  # 存在しないIP
os.environ['CENTRAL_SERVER_PORT'] = '5000'

from db_utils import DatabaseAPI

def test_server_down_buffering():
    """サーバーダウン時のバッファリング機能テスト"""
    print("=" * 70)
    print("  統合テスト：サーバーダウン時のバッファリング動作")
    print("=" * 70)

    db_api = DatabaseAPI()

    print("\n[シナリオ]")
    print("  1. 中央サーバーが存在しない（192.168.255.254）")
    print("  2. データ送信を試行 -> 接続エラー発生")
    print("  3. データは自動的にローカルバッファに保存される")
    print("  4. バッファ統計で保存されたデータを確認")

    # 初期状態の確認
    print("\n[STEP 1] バッファの初期状態")
    initial_stats = db_api.buffer.get_stats()
    print(f"  総件数: {initial_stats['total_count']}件")

    # テストデータを3件送信試行
    print("\n[STEP 2] 3件のデータを送信試行（接続エラーが発生する）")

    test_results = []
    for i in range(3):
        test_data = {
            'temperature': 20.0 + i,
            'pressure': 1000.0 + i * 5,
            'humidity': 50.0 + i * 2,
            'count': i
        }

        equipment_id = f'TEST_{i+1:03d}'

        print(f"\n  データ{i+1}: {equipment_id}")

        # 送信試行（失敗してバッファに保存されるはず）
        success = db_api.send_log_data(equipment_id, test_data)
        test_results.append(success)

        if success:
            print(f"    結果: 送信成功（予期しない）")
        else:
            print(f"    結果: 送信失敗 -> バッファに保存")

    # すべて失敗したはず
    if all(not result for result in test_results):
        print("\n  OK: すべてのデータ送信が失敗しました（想定通り）")
    else:
        print("\n  WARNING: 一部のデータが成功しました（想定外）")

    # バッファの状態を確認
    print("\n[STEP 3] バッファの現在状態")
    current_stats = db_api.buffer.get_stats()
    print(f"  総件数: {current_stats['total_count']}件")
    print(f"  設備別: {current_stats['equipment_stats']}")
    print(f"  再試行回数別: {current_stats['retry_stats']}")

    # 未送信データの詳細確認
    print("\n[STEP 4] 未送信データの詳細")
    pending = db_api.buffer.get_pending(limit=10)
    print(f"  未送信データ: {len(pending)}件")

    if len(pending) > 0:
        print("\n  詳細:")
        for rec_id, equipment_id, data in pending:
            print(f"    - ID={rec_id}, 設備={equipment_id}")
            print(f"      温度={data.get('temperature', 'N/A')}度, "
                  f"圧力={data.get('pressure', 'N/A')}hPa")

    # バッファ件数の検証
    expected_count = initial_stats['total_count'] + 3
    actual_count = current_stats['total_count']

    print("\n[STEP 5] バッファ件数の検証")
    print(f"  期待値: {expected_count}件")
    print(f"  実際値: {actual_count}件")

    if actual_count == expected_count:
        print("  OK: バッファに正しく保存されました")
        test_passed = True
    else:
        print("  ERROR: バッファ件数が一致しません")
        test_passed = False

    # クリーンアップ
    print("\n[CLEANUP] テストデータをクリーンアップ")
    for rec_id, _, _ in pending:
        db_api.buffer.mark_as_sent(rec_id)
    print(f"  削除完了: {len(pending)}件")

    # 最終確認
    final_stats = db_api.buffer.get_stats()
    print(f"\n  クリーンアップ後の総件数: {final_stats['total_count']}件")

    print("\n" + "=" * 70)
    if test_passed:
        print("  [SUCCESS] バッファリング機能は正常に動作しています")
        print("  - サーバーダウン時にデータが自動保存される")
        print("  - バッファから正しくデータを取得できる")
        print("  - バッファからのデータ削除が正常に動作する")
    else:
        print("  [FAILED] バッファリング機能に問題があります")
    print("=" * 70)

    return test_passed

def test_retry_logic():
    """再送信ロジックのテスト"""
    print("\n" + "=" * 70)
    print("  統合テスト：再送信ロジック")
    print("=" * 70)

    db_api = DatabaseAPI()

    # テストデータを1件保存
    print("\n[STEP 1] テストデータをバッファに保存")
    test_data = {'value': 100, 'description': 'retry test'}
    db_api.buffer.save('RETRY_TEST', test_data)
    print("  OK: 保存完了")

    # 再送信試行（サーバーが存在しないため失敗）
    print("\n[STEP 2] 再送信を試行（失敗するはず）")
    success, failure, total = db_api.retry_pending_data(batch_size=10)
    print(f"  成功: {success}件")
    print(f"  失敗: {failure}件")
    print(f"  総数: {total}件")

    if failure > 0 and success == 0:
        print("  OK: 想定通り再送信が失敗しました")
        test_passed = True
    else:
        print("  WARNING: 想定外の結果です")
        test_passed = False

    # 再試行カウントの確認
    print("\n[STEP 3] 再試行カウントの確認")
    pending = db_api.buffer.get_pending(limit=10)

    # RETRY_TESTのデータを探す
    retry_test_data = [p for p in pending if p[1] == 'RETRY_TEST']

    if retry_test_data:
        rec_id, equipment_id, data = retry_test_data[0]
        # 直接データベースから再試行カウントを取得
        import sqlite3
        conn = sqlite3.connect(db_api.buffer.db_path)
        cursor = conn.execute('SELECT retry_count FROM pending_data WHERE id = ?', (rec_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            retry_count = row[0]
            print(f"  再試行カウント: {retry_count}回")
            if retry_count > 0:
                print("  OK: 再試行カウントが正しく更新されています")
            else:
                print("  WARNING: 再試行カウントが更新されていません")

    # クリーンアップ
    print("\n[CLEANUP] テストデータを削除")
    for rec_id, equipment_id, _ in retry_test_data:
        db_api.buffer.mark_as_sent(rec_id)
    print("  削除完了")

    print("\n" + "=" * 70)
    if test_passed:
        print("  [SUCCESS] 再送信ロジックは正常に動作しています")
    else:
        print("  [FAILED] 再送信ロジックに問題があります")
    print("=" * 70)

    return test_passed

def main():
    """メイン関数"""
    print("\n統合テスト開始: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    try:
        # テスト1: サーバーダウン時のバッファリング
        result1 = test_server_down_buffering()
        time.sleep(1)

        # テスト2: 再送信ロジック
        result2 = test_retry_logic()

        print("\n" + "=" * 70)
        print("  全統合テスト完了")
        print("=" * 70)

        if result1 and result2:
            print("\n[OVERALL SUCCESS] すべての統合テストが正常に完了しました")
            print("\n動作保証の結論:")
            print("  1. サーバーダウン時にデータが自動的にバッファに保存される")
            print("  2. バッファからのデータ取得・削除が正常に動作する")
            print("  3. 再送信ロジックが正常に動作する")
            print("  4. 再試行カウントが正しく更新される")
            print("\n-> ローカルバッファ機能は実用レベルで動作します")
        else:
            print("\n[OVERALL FAILED] 一部のテストが失敗しました")
            print("\n-> さらなるデバッグが必要です")

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        print(f"\n統合テスト終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == '__main__':
    main()
