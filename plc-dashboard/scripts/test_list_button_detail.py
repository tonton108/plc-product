"""
リスト表示のボタンを拡大して詳細確認
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_list_button_detail():
    """ボタンの詳細を確認"""
    print("=" * 70)
    print("  List Button Detail Test")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            # ブラウザを起動（拡大表示）
            print("\n[1/5] ブラウザを起動中...")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()

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

            # リスト表示に切り替え
            print("\n[4/5] リスト表示に切り替え中...")
            list_button = page.locator('button:has-text("リスト")')
            list_button.click()
            time.sleep(1)

            # データテーブルが表示されるまで待機
            page.wait_for_selector('.v-data-table', timeout=5000)

            # スクリーンショット撮影
            print("\n[5/5] スクリーンショット撮影中...")

            # 最初の行のアクションセルを取得
            first_row_actions = page.locator('.v-data-table tbody tr').first.locator('td').last

            # アクションセル部分のスクリーンショット
            screenshot_path = Path(__file__).parent / 'list_button_detail.png'
            first_row_actions.screenshot(path=str(screenshot_path))
            print(f"  [OK] 詳細スクリーンショット保存: {screenshot_path}")

            # 計算されたスタイルを詳細に取得
            print("\n[追加] ボタンの詳細スタイル情報を取得中...")
            button_detail = page.evaluate('''() => {
                const btn = document.querySelector('.v-data-table .list-action-btn');
                if (!btn) return null;

                const btnStyles = window.getComputedStyle(btn);
                const content = btn.querySelector('.v-btn__content');
                const contentStyles = content ? window.getComputedStyle(content) : null;
                const icon = btn.querySelector('.v-icon');
                const iconStyles = icon ? window.getComputedStyle(icon) : null;

                return {
                    button: {
                        height: btnStyles.height,
                        minHeight: btnStyles.minHeight,
                        padding: btnStyles.padding,
                        display: btnStyles.display,
                    },
                    content: contentStyles ? {
                        height: contentStyles.height,
                        display: contentStyles.display,
                        alignItems: contentStyles.alignItems,
                        justifyContent: contentStyles.justifyContent,
                        lineHeight: contentStyles.lineHeight,
                        padding: contentStyles.padding,
                    } : null,
                    icon: iconStyles ? {
                        lineHeight: iconStyles.lineHeight,
                        verticalAlign: iconStyles.verticalAlign,
                        alignSelf: iconStyles.alignSelf,
                        fontSize: iconStyles.fontSize,
                    } : null
                };
            }''')

            if button_detail:
                print("  [OK] ボタン詳細スタイル:")
                print(f"\n  ボタン本体:")
                for key, value in button_detail['button'].items():
                    print(f"    {key}: {value}")

                if button_detail['content']:
                    print(f"\n  .v-btn__content:")
                    for key, value in button_detail['content'].items():
                        print(f"    {key}: {value}")

                if button_detail['icon']:
                    print(f"\n  .v-icon:")
                    for key, value in button_detail['icon'].items():
                        print(f"    {key}: {value}")

            print("\n" + "=" * 70)
            print("  Test Results")
            print("=" * 70)
            print(f"\n[SUCCESS] 詳細確認完了")
            print(f"\nスクリーンショット: {screenshot_path}")

            print("\nブラウザは5秒後に自動的に閉じます...")
            time.sleep(5)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] エラーが発生しました: {e}")
            try:
                screenshot_path = Path(__file__).parent / 'list_button_detail_error.png'
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
    success = test_list_button_detail()
    sys.exit(0 if success else 1)
