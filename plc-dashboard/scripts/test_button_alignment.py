"""
ボタン内のアイコンとテキストの垂直方向配置を確認するテスト
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_button_alignment():
    """ボタンの配置を確認"""
    print("=" * 70)
    print("  Button Alignment Test")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            # ブラウザを起動
            print("\n[1/4] ブラウザを起動中...")
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # ログインページを開く
            print("\n[2/4] ログインページを開く...")
            page.goto('http://localhost:3000/', timeout=15000)

            # ログイン
            print("\n[3/4] ログイン中...")
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            page.wait_for_function('window.location.pathname !== "/login"', timeout=10000)
            time.sleep(2)
            print(f"  [OK] ログイン成功: {page.url}")

            # 設備カードが表示されるまで待機
            page.wait_for_selector('.glass-card', timeout=10000)
            print("  [OK] 設備カード表示")

            # スクリーンショット撮影
            print("\n[4/4] スクリーンショット撮影中...")
            screenshot_path = Path(__file__).parent / 'button_alignment_test.png'

            # 最初の設備カードにフォーカス
            first_card = page.locator('.glass-card').first
            first_card.scroll_into_view_if_needed()

            # カード部分のスクリーンショットを撮影
            first_card.screenshot(path=str(screenshot_path))
            print(f"  [OK] スクリーンショット保存: {screenshot_path}")

            print("\n" + "=" * 70)
            print("  Test Results")
            print("=" * 70)
            print(f"\n[SUCCESS] ボタン配置テスト完了")
            print(f"\nスクリーンショット: {screenshot_path}")
            print("\nボタン内のアイコンとテキストが垂直方向で中央に配置されているか確認してください。")

            print("\nブラウザは5秒後に自動的に閉じます...")
            time.sleep(5)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] エラーが発生しました: {e}")
            try:
                screenshot_path = Path(__file__).parent / 'button_alignment_error.png'
                page.screenshot(path=str(screenshot_path))
                print(f"  エラースクリーンショット: {screenshot_path}")
            except:
                pass
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    success = test_button_alignment()
    sys.exit(0 if success else 1)
