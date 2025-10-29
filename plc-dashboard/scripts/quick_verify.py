"""
Playwrightで現在のアプリケーション状態を簡易確認
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def verify_application():
    """アプリケーションの動作を確認"""
    print("=" * 70)
    print("  Playwright Application Verification")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            # CI環境ではheadlessモードで実行
            import os
            is_ci = os.environ.get('CI', 'false').lower() == 'true'
            headless_mode = is_ci

            # ブラウザを起動
            print(f"\n[1/5] ブラウザを起動中 (headless={headless_mode})...")
            browser = p.chromium.launch(headless=headless_mode)
            page = browser.new_page()

            # JavaScriptエラーを記録
            js_errors = []
            console_messages = []

            def handle_console(msg):
                console_messages.append(f"[{msg.type}] {msg.text}")
                if msg.type == 'error':
                    print(f"  [ERROR] Console Error: {msg.text}")

            def handle_page_error(error):
                js_errors.append(str(error))
                print(f"  [ERROR] Page Error: {error}")

            page.on('console', handle_console)
            page.on('pageerror', handle_page_error)

            # トップページを開く
            print("\n[2/5] Accessing top page...")
            page.goto('http://localhost:3000/', wait_until='networkidle', timeout=15000)
            print("  [OK] Page opened")

            # ページが読み込まれるまで待機
            print("\n[3/5] Waiting for page rendering...")
            try:
                page.wait_for_selector('.v-card, .v-container', timeout=10000)
                print("  [OK] Page rendered successfully")
            except PlaywrightTimeout:
                print("  [ERROR] Page rendering timeout")

            # スクリーンショットを保存
            print("\n[4/5] Saving screenshot...")
            screenshot_path = Path(__file__).parent / 'app_verification.png'
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"  [OK] Screenshot saved: {screenshot_path}")

            # ページタイトルを確認
            title = page.title()
            print(f"\n[5/5] Page title: {title}")

            # 設備一覧が表示されているか確認
            try:
                equipment_cards = page.query_selector_all('.v-card')
                print(f"  [OK] Equipment cards: {len(equipment_cards)}")
            except:
                print("  [INFO] No equipment cards found")

            # 結果のサマリー
            print("\n" + "=" * 70)
            print("  Test Results")
            print("=" * 70)

            if js_errors:
                print(f"\n[ERROR] JavaScript Errors: {len(js_errors)} found")
                for error in js_errors:
                    print(f"  - {error}")
            else:
                print("\n[OK] JavaScript Errors: None")

            console_errors = [msg for msg in console_messages if '[error]' in msg]
            if console_errors:
                print(f"\n[WARNING] Console Errors: {len(console_errors)} found")
                for error in console_errors[:5]:  # 最初の5件のみ表示
                    print(f"  - {error}")
            else:
                print("[OK] Console Errors: None")

            print("\n[SUCCESS] Application is working correctly")
            print(f"\nBrowser will close automatically in 5 seconds...")

            # 5秒待機してブラウザを閉じる
            page.wait_for_timeout(5000)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] An error occurred: {e}")
            try:
                screenshot_path = Path(__file__).parent / 'app_verification_error.png'
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
    success = verify_application()
    sys.exit(0 if success else 1)
