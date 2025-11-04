"""
Phase 4統合テスト: エラーレポーター + PLCエージェント

このスクリプトは、error_reporter.pyとplc_agent.pyの統合をテストします。
"""
import os
import sys
import time
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数設定
os.environ["USE_DUMMY_PLC"] = "true"
os.environ["CENTRAL_SERVER_URL"] = "http://localhost:5000"

# テスト用設備ID（既存の設備を使用）
TEST_EQUIPMENT_ID = "DEMO_001"

def test_error_reporter():
    """エラーレポーターの基本機能テスト"""
    from error_reporter import initialize_error_reporter, report_error, report_alarm

    print("=" * 60)
    print("Phase 4統合テスト開始")
    print("=" * 60)

    # 1. エラーレポーター初期化
    print("\n[TEST 1] エラーレポーター初期化テスト")
    initialize_error_reporter(TEST_EQUIPMENT_ID, "http://localhost:5000")
    print("[OK] 初期化成功")

    # 2. 通信エラー送信テスト
    print("\n[TEST 2] 通信エラー送信テスト")
    result = report_error(
        error_type="CONNECTION_FAILED",
        error_message="テスト: PLC接続失敗",
        retry_count=0,
        plc_ip="192.168.1.100",
        protocol="MC_PROTOCOL_3E"
    )
    if result:
        print("[OK] エラーログ送信成功")
    else:
        print("[FAIL] エラーログ送信失敗")

    time.sleep(1)

    # 3. アラーム送信テスト
    print("\n[TEST 3] アラーム送信テスト")
    result = report_alarm(
        alarm_code="E001",
        alarm_level="WARNING",
        alarm_message="テスト: 温度異常検出",
        alarm_data={
            "temperature": 45.5,
            "threshold": 40.0
        }
    )
    if result:
        print("[OK] アラーム送信成功")
    else:
        print("[FAIL] アラーム送信失敗")

    time.sleep(1)

    # 4. CRITICAL レベルのアラーム送信テスト
    print("\n[TEST 4] CRITICAL アラーム送信テスト")
    result = report_alarm(
        alarm_code="E002",
        alarm_level="CRITICAL",
        alarm_message="テスト: 設備停止アラーム",
        alarm_data={
            "error_code": 2,
            "reason": "緊急停止ボタン押下"
        }
    )
    if result:
        print("[OK] CRITICAL アラーム送信成功")
    else:
        print("[FAIL] CRITICAL アラーム送信失敗")

    print("\n" + "=" * 60)
    print("Phase 4統合テスト完了")
    print("=" * 60)
    print("\n次のコマンドでサーバー側のデータを確認してください:")
    print(f"  curl http://localhost:5000/api/equipment/{TEST_EQUIPMENT_ID}/error_logs")
    print(f"  curl http://localhost:5000/api/equipment/{TEST_EQUIPMENT_ID}/alarms")


if __name__ == "__main__":
    try:
        test_error_reporter()
    except KeyboardInterrupt:
        print("\n\n⚠️ テストが中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
