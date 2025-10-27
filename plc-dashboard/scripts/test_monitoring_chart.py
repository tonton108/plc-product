"""
モニタリング画面のグラフ更新をテスト
カードが再レンダリングされずに、グラフだけが更新されることを確認
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_monitoring_chart():
    """モニタリング画面のグラフ更新をテスト"""
    print("=" * 70)
    print("  Monitoring Chart Update Test")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            # ブラウザを起動（実際のブラウザを表示）
            print("\n[1/7] Launching browser...")
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # ログインページを開く
            print("\n[2/7] Opening login page...")
            page.goto('http://localhost:3000/', timeout=15000)
            print("  [OK] Page opened")

            # ログイン
            print("\n[3/7] Logging in...")
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')

            # ログイン後のページ遷移を待つ（URLがログインページから変わるまで）
            page.wait_for_function('window.location.pathname !== "/login"', timeout=10000)
            time.sleep(2)  # ページの読み込みを待つ
            print(f"  [OK] Logged in successfully, current URL: {page.url}")

            # モニタリングページに直接アクセス（LINE_A_001を使用）
            print("\n[4/7] Navigating to monitoring page...")
            equipment_id = "LINE_A_001"
            page.goto(f'http://localhost:3000/monitoring/{equipment_id}', timeout=15000)
            print(f"  [OK] Navigated to monitoring page: {equipment_id}")

            # モニタリング画面が表示されるまで待機
            print("\n[5/7] Waiting for monitoring page to load...")
            page.wait_for_selector('.glass-card', timeout=10000)
            print("  [OK] Monitoring page loaded")

            # スクリーンショット1: 初期状態
            screenshot_path_1 = Path(__file__).parent / 'monitoring_chart_before.png'
            page.screenshot(path=str(screenshot_path_1), full_page=True)
            print(f"  [OK] Screenshot saved: {screenshot_path_1}")

            # グラフカードの数を数える
            chart_cards = page.locator('.glass-card:has(canvas)').count()
            print(f"\n[6/7] Chart cards found: {chart_cards}")

            if chart_cards == 0:
                print("  [WARNING] No chart cards found")
            else:
                # 10秒待機してデータ更新を観察
                print("\n[7/7] Observing chart updates for 10 seconds...")
                print("  Watch the browser: Cards should NOT flicker,")
                print("  only the line charts (canvas) should update smoothly.")

                time.sleep(10)

                # スクリーンショット2: データ更新後
                screenshot_path_2 = Path(__file__).parent / 'monitoring_chart_after.png'
                page.screenshot(path=str(screenshot_path_2), full_page=True)
                print(f"  [OK] Screenshot saved: {screenshot_path_2}")

            print("\n" + "=" * 70)
            print("  Test Results")
            print("=" * 70)
            print("\n[SUCCESS] Monitoring chart test completed")
            print("\nPlease check:")
            print("  1. Cards should NOT flicker or re-render")
            print("  2. Only the line charts (canvas) should update")
            print("  3. Chart data should increase smoothly")
            print(f"\nScreenshots:")
            print(f"  Before: {screenshot_path_1}")
            print(f"  After:  {screenshot_path_2}")

            print("\nBrowser will close in 5 seconds...")
            time.sleep(5)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] An error occurred: {e}")
            try:
                screenshot_path = Path(__file__).parent / 'monitoring_chart_error.png'
                page.screenshot(path=str(screenshot_path))
                print(f"  Error screenshot saved: {screenshot_path}")
            except:
                pass
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    success = test_monitoring_chart()
    sys.exit(0 if success else 1)
