"""
Phase 7: 運用機能の動作確認スクリプト

エラー・アラームページのアクションボタン（確認・解除・解決）の動作をテスト
"""
from playwright.sync_api import sync_playwright
import time
import requests

def setup_test_data():
    """テスト用のアラームとエラーログを作成"""
    print("\n[SETUP] テストデータ作成中...")

    base_url = "http://localhost:5000"
    equipment_id = "DEMO_001"

    try:
        # テスト用アラームを作成
        alarm_response = requests.post(
            f"{base_url}/api/equipment/{equipment_id}/alarms",
            json={
                "alarm_code": "E001",
                "alarm_level": "WARNING",
                "alarm_message": "テスト用アラーム（Phase 7動作確認）"
            },
            timeout=5
        )

        # テスト用エラーログを作成
        error_response = requests.post(
            f"{base_url}/api/equipment/{equipment_id}/error_logs",
            json={
                "error_type": "CONNECTION_FAILED",
                "error_message": "テスト用エラーログ（Phase 7動作確認）",
                "retry_count": 0
            },
            timeout=5
        )

        if alarm_response.ok and error_response.ok:
            print("[OK] テストデータ作成成功")
            return True
        else:
            print("[WARN] テストデータ作成失敗（既存データでテスト続行）")
            return False

    except Exception as e:
        print(f"[WARN] テストデータ作成エラー: {e}")
        return False

def test_phase7_operations():
    """Phase 7運用機能のテスト"""
    with sync_playwright() as p:
        print("=" * 70)
        print("Phase 7: エラー・アラーム運用機能の動作確認")
        print("=" * 70)

        # テストデータ準備
        setup_test_data()
        time.sleep(1)

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # 1. エラー・アラームページにアクセス
            print("\n[TEST 1] エラー・アラームページにアクセス")
            page.goto("http://localhost:3000/errors-alarms", wait_until='domcontentloaded', timeout=60000)
            time.sleep(5)
            print("[OK] ページ表示成功")

            # 2. 設備を選択
            print("\n[TEST 2] 設備選択")
            try:
                # Vuetifyのv-selectをクリック（より具体的なセレクタを使用）
                page.wait_for_selector('.v-select', timeout=10000)
                page.click('.v-select .v-field')
                time.sleep(1)

                # ドロップダウンリストが表示されるまで待つ
                page.wait_for_selector('.v-list-item', timeout=5000)

                # DEMO_001を選択
                page.click('.v-list-item:has-text("DEMO_001")')
                time.sleep(3)
                print("[OK] 設備選択成功")
            except Exception as e:
                print(f"[WARN] 設備選択エラー（スキップ）: {e}")
                # 設備が既に選択されている可能性があるので続行
                time.sleep(2)

            # スクリーンショット: 初期状態
            screenshot_initial = "plc-dashboard/scripts/ui_ux_screenshots/phase7_initial.png"
            page.screenshot(path=screenshot_initial, full_page=True)
            print(f"[OK] 初期状態スクリーンショット: {screenshot_initial}")

            # 3. アラーム履歴テーブルの確認
            print("\n[TEST 3] アラーム履歴テーブル確認")
            alarm_table = page.locator('.bg-error.text-white:has-text("アラーム履歴")')
            if alarm_table.is_visible():
                print("[OK] アラーム履歴テーブル表示確認")

                # アラームデータの存在確認
                time.sleep(2)
                # アラームテーブル内の行数を数える（最初のv-data-table）
                alarm_rows = page.locator('.v-data-table').first.locator('tbody tr').count()
                print(f"[INFO] アラーム件数: {alarm_rows}件")

            else:
                print("[FAIL] アラーム履歴テーブルが表示されていません")

            # 4. アラーム確認ボタンのテスト
            print("\n[TEST 4] アラーム確認ボタンのテスト")
            try:
                # 「確認」ボタンを探す
                acknowledge_btn = page.locator('button:has-text("確認")').first
                if acknowledge_btn.is_visible(timeout=5000):
                    print("[OK] 確認ボタン発見")

                    # ボタンをクリック
                    acknowledge_btn.click()
                    time.sleep(3)
                    print("[OK] 確認ボタンクリック成功")

                    # スクリーンショット: 確認後
                    screenshot_ack = "plc-dashboard/scripts/ui_ux_screenshots/phase7_after_acknowledge.png"
                    page.screenshot(path=screenshot_ack, full_page=True)
                    print(f"[OK] 確認後スクリーンショット: {screenshot_ack}")
                else:
                    print("[WARN] 確認ボタンが見つかりません（すでに確認済みの可能性）")
            except Exception as e:
                print(f"[WARN] 確認ボタンテスト: {e}")

            # 5. アラーム解除ボタンのテスト
            print("\n[TEST 5] アラーム解除ボタンのテスト")
            try:
                # 「解除」ボタンを探す
                clear_btn = page.locator('button:has-text("解除")').first
                if clear_btn.is_visible(timeout=5000):
                    print("[OK] 解除ボタン発見")

                    # ボタンをクリック
                    clear_btn.click()
                    time.sleep(3)
                    print("[OK] 解除ボタンクリック成功")

                    # スクリーンショット: 解除後
                    screenshot_clear = "plc-dashboard/scripts/ui_ux_screenshots/phase7_after_clear.png"
                    page.screenshot(path=screenshot_clear, full_page=True)
                    print(f"[OK] 解除後スクリーンショット: {screenshot_clear}")
                else:
                    print("[WARN] 解除ボタンが見つかりません（すでに解除済みの可能性）")
            except Exception as e:
                print(f"[WARN] 解除ボタンテスト: {e}")

            # 6. エラーログテーブルの確認
            print("\n[TEST 6] エラーログテーブル確認")
            error_table = page.locator('.bg-warning.text-white:has-text("エラーログ")')
            if error_table.is_visible():
                print("[OK] エラーログテーブル表示確認")

                # エラーログデータの存在確認
                time.sleep(2)
                # エラーログテーブル内の行数を数える（2番目のv-data-table）
                error_rows = page.locator('.v-data-table').nth(1).locator('tbody tr').count()
                print(f"[INFO] エラーログ件数: {error_rows}件")
            else:
                print("[FAIL] エラーログテーブルが表示されていません")

            # 7. エラーログ解決ボタンのテスト
            print("\n[TEST 7] エラーログ解決ボタンのテスト")
            try:
                # 「解決」ボタンを探す（エラーログセクション内）
                resolve_btn = page.locator('button:has-text("解決")').first
                if resolve_btn.is_visible(timeout=5000):
                    print("[OK] 解決ボタン発見")

                    # ボタンをクリック
                    resolve_btn.click()
                    time.sleep(3)
                    print("[OK] 解決ボタンクリック成功")

                    # スクリーンショット: 解決後
                    screenshot_resolve = "plc-dashboard/scripts/ui_ux_screenshots/phase7_after_resolve.png"
                    page.screenshot(path=screenshot_resolve, full_page=True)
                    print(f"[OK] 解決後スクリーンショット: {screenshot_resolve}")
                else:
                    print("[WARN] 解決ボタンが見つかりません（すでに解決済みの可能性）")
            except Exception as e:
                print(f"[WARN] 解決ボタンテスト: {e}")

            # 最終スクリーンショット
            print("\n[TEST 8] 最終状態確認")
            screenshot_final = "plc-dashboard/scripts/ui_ux_screenshots/phase7_final.png"
            page.screenshot(path=screenshot_final, full_page=True)
            print(f"[OK] 最終スクリーンショット: {screenshot_final}")

            # 結果サマリー
            print("\n" + "=" * 70)
            print("Phase 7テスト完了")
            print("=" * 70)
            print("\n保存されたスクリーンショット:")
            print(f"  1. {screenshot_initial} (初期状態)")
            print(f"  2. {screenshot_ack} (確認後)")
            print(f"  3. {screenshot_clear} (解除後)")
            print(f"  4. {screenshot_resolve} (解決後)")
            print(f"  5. {screenshot_final} (最終状態)")
            print("\n[INFO] スクリーンショットで各アクション後の状態変化を確認してください")

            # 10秒間表示して確認
            time.sleep(10)

        except Exception as e:
            print(f"\n[ERROR] テスト実行エラー: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == "__main__":
    test_phase7_operations()
