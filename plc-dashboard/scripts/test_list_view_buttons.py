"""
リスト表示のボタンの配置を確認するテスト
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_list_view_buttons():
    """リスト表示のボタンを確認"""
    print("=" * 70)
    print("  List View Button Test")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            # ブラウザを起動
            print("\n[1/5] ブラウザを起動中...")
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # ログインページを開く
            print("\n[2/5] ログインページを開く...")
            page.goto('http://localhost:3000/', timeout=15000)

            # ログイン
            print("\n[3/5] ログイン中...")
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            page.wait_for_function('window.location.pathname !== "/login"', timeout=10000)
            time.sleep(2)
            print(f"  [OK] ログイン成功: {page.url}")

            # 設備カードが表示されるまで待機
            page.wait_for_selector('.glass-card', timeout=10000)
            print("  [OK] 設備カード表示")

            # リスト表示に切り替え
            print("\n[4/5] リスト表示に切り替え中...")
            list_button = page.locator('button:has-text("リスト")')
            list_button.click()
            time.sleep(1)
            print("  [OK] リスト表示に切り替え")

            # データテーブルが表示されるまで待機
            page.wait_for_selector('.v-data-table', timeout=5000)

            # スクリーンショット撮影
            print("\n[5/5] スクリーンショット撮影中...")
            screenshot_path = Path(__file__).parent / 'list_view_buttons_test.png'
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"  [OK] スクリーンショット保存: {screenshot_path}")

            # テーブル内のボタンの詳細を取得
            print("\n[追加] ボタンのスタイル情報を取得中...")
            button_info = page.evaluate('''() => {
                const buttons = document.querySelectorAll('.v-data-table button');
                const info = [];
                buttons.forEach((btn, index) => {
                    const content = btn.querySelector('.v-btn__content');
                    const icon = btn.querySelector('.v-icon');
                    const text = btn.textContent.trim();
                    if (content && (text.includes('監視') || text.includes('ログ'))) {
                        const contentStyles = window.getComputedStyle(content);
                        const iconStyles = icon ? window.getComputedStyle(icon) : null;
                        info.push({
                            index: index,
                            text: text,
                            contentDisplay: contentStyles.display,
                            contentAlignItems: contentStyles.alignItems,
                            contentFlexDirection: contentStyles.flexDirection,
                            iconAlignSelf: iconStyles ? iconStyles.alignSelf : 'N/A'
                        });
                    }
                });
                return info;
            }''')

            if button_info:
                print("  [OK] ボタンスタイル情報:")
                for info in button_info:
                    print(f"    ボタン: {info['text']}")
                    print(f"      .v-btn__content display: {info['contentDisplay']}")
                    print(f"      .v-btn__content align-items: {info['contentAlignItems']}")
                    print(f"      .v-btn__content flex-direction: {info['contentFlexDirection']}")
                    print(f"      .v-icon align-self: {info['iconAlignSelf']}")
                    print()

            print("=" * 70)
            print("  Test Results")
            print("=" * 70)
            print(f"\n[SUCCESS] リスト表示ボタンテスト完了")
            print(f"\nスクリーンショット: {screenshot_path}")
            print("\nリスト表示のボタンが正しく配置されているか確認してください。")

            print("\nブラウザは5秒後に自動的に閉じます...")
            time.sleep(5)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] エラーが発生しました: {e}")
            try:
                screenshot_path = Path(__file__).parent / 'list_view_buttons_error.png'
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
    success = test_list_view_buttons()
    sys.exit(0 if success else 1)
