"""
モニタリング画面のPlaywrightテスト
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pathlib import Path

def test_monitoring_page(equipment_id="LINE_A_001"):
    """モニタリング画面のテスト"""
    print(f"\n[INFO] モニタリング画面テスト: {equipment_id}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # JavaScriptエラーを記録
            js_errors = []
            console_errors = []

            def handle_console(msg):
                if msg.type == 'error':
                    console_errors.append(msg.text)
                    print(f"[WARNING] JS Console Error: {msg.text}")

            def handle_page_error(error):
                js_errors.append(str(error))
                print(f"[ERROR] Page Error: {error}")

            page.on('console', handle_console)
            page.on('pageerror', handle_page_error)

            # モニタリング画面を開く
            monitoring_url = f"http://localhost:3000/monitoring/{equipment_id}"
            print(f"[INFO] アクセス中: {monitoring_url}")
            page.goto(monitoring_url, wait_until='networkidle', timeout=15000)

            # ページのレンダリングを待つ
            print("[INFO] ページのレンダリングを待機中...")
            try:
                # モニタリング画面の特徴的な要素を待つ（グラフ、データカード等）
                page.wait_for_selector('.v-card, canvas, [class*="chart"]', timeout=10000)
                print("[OK] モニタリング画面が表示されました")

                # スクリーンショットを保存
                screenshot_path = Path(__file__).parent / f'monitoring_{equipment_id}_screenshot.png'
                page.screenshot(path=str(screenshot_path))
                print(f"[INFO] スクリーンショット保存: {screenshot_path}")

            except PlaywrightTimeout:
                print("[ERROR] モニタリング画面のレンダリングがタイムアウトしました")
                screenshot_path = Path(__file__).parent / f'monitoring_{equipment_id}_error.png'
                page.screenshot(path=str(screenshot_path))
                print(f"[INFO] エラースクリーンショット保存: {screenshot_path}")
                browser.close()
                return False

            # JavaScriptエラーチェック
            if js_errors or console_errors:
                print("[ERROR] JavaScriptエラーが検出されました:")
                for error in js_errors:
                    print(f"  - Page Error: {error}")
                for error in console_errors:
                    print(f"  - Console Error: {error}")
                browser.close()
                return False

            print("[OK] JavaScriptエラーなし")
            browser.close()
            return True

        except Exception as e:
            print(f"[ERROR] テストエラー: {e}")
            try:
                screenshot_path = Path(__file__).parent / f'monitoring_{equipment_id}_exception.png'
                page.screenshot(path=str(screenshot_path))
                print(f"[INFO] 例外発生時スクリーンショット: {screenshot_path}")
            except:
                pass
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    success = test_monitoring_page("LINE_A_001")
    if success:
        print("\n[SUCCESS] モニタリング画面テスト成功！")
        exit(0)
    else:
        print("\n[FAILED] モニタリング画面テスト失敗")
        exit(1)
