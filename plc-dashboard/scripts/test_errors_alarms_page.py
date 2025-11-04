"""
エラー・アラームページの動作確認スクリプト

Phase 5: フロントエンド実装のテスト
"""
from playwright.sync_api import sync_playwright
import time

def test_errors_alarms_page():
    with sync_playwright() as p:
        print("=" * 60)
        print("Phase 5: エラー・アラームページ動作確認")
        print("=" * 60)

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # 1. エラー・アラームページに直接移動
            print("\n[TEST 1] エラー・アラームページにアクセス")
            page.goto("http://localhost:3000/errors-alarms")
            time.sleep(3)
            print("[OK] エラー・アラームページ表示成功")

            # スクリーンショット撮影
            screenshot_path = "plc-dashboard/scripts/ui_ux_screenshots/errors_alarms_page.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"[OK] スクリーンショット保存: {screenshot_path}")

            # 3. 設備を選択
            print("\n[TEST 3] 設備選択")
            page.click('div.v-select')
            time.sleep(1)

            # DEMO_001を選択（リストの最初の項目）
            page.click('div.v-list-item:has-text("DEMO_001")')
            time.sleep(2)
            print("[OK] 設備選択成功")

            # 4. PLC状態カードの確認
            print("\n[TEST 4] PLC状態カード確認")
            plc_status_visible = page.locator('text=PLC通信状態').is_visible()
            if plc_status_visible:
                print("[OK] PLC状態カード表示確認")
            else:
                print("[FAIL] PLC状態カードが表示されていません")

            # 5. アラーム履歴テーブルの確認
            print("\n[TEST 5] アラーム履歴テーブル確認")
            alarms_table_visible = page.locator('text=アラーム履歴').is_visible()
            if alarms_table_visible:
                print("[OK] アラーム履歴テーブル表示確認")
            else:
                print("[FAIL] アラーム履歴テーブルが表示されていません")

            # 6. エラーログテーブルの確認
            print("\n[TEST 6] エラーログテーブル確認")
            error_logs_table_visible = page.locator('text=エラーログ').is_visible()
            if error_logs_table_visible:
                print("[OK] エラーログテーブル表示確認")
            else:
                print("[FAIL] エラーログテーブルが表示されていません")

            # 最終スクリーンショット
            screenshot_path_final = "plc-dashboard/scripts/ui_ux_screenshots/errors_alarms_page_with_data.png"
            page.screenshot(path=screenshot_path_final, full_page=True)
            print(f"[OK] 最終スクリーンショット保存: {screenshot_path_final}")

            print("\n" + "=" * 60)
            print("Phase 5テスト完了")
            print("=" * 60)
            print("\nスクリーンショットを確認してください:")
            print(f"  - {screenshot_path}")
            print(f"  - {screenshot_path_final}")

            # 5秒間表示して確認
            time.sleep(5)

        except Exception as e:
            print(f"\n[ERROR] テスト実行エラー: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == "__main__":
    test_errors_alarms_page()
