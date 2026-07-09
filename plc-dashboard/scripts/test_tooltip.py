"""
ツールチップの表示テスト（ダークモード）
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_tooltip():
    """ツールチップの表示をテスト"""
    print("=" * 70)
    print("  Tooltip Display Test (Dark Mode)")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            # ブラウザを起動（headless=False で実際の表示を確認）
            print("\n[1/8] ブラウザを起動中...")
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # ログインページを開く
            print("\n[2/8] ログインページを開く...")
            page.goto('http://localhost:3000/', timeout=15000)
            print("  [OK] ページ表示")

            # ログイン
            # Phase 1認証対応: 資格情報はバックエンドのシードユーザー
            # （flask auth seed --admin-password plc-monitor-2025 で作成）と一致させる。
            # ボタンは言語非依存のtype=submitで特定（CI英語ロケール対策、test_monitoring_chart.pyと同じ方式）
            print("\n[3/8] ログイン中...")
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button[type="submit"]')
            page.wait_for_function('window.location.pathname !== "/login"', timeout=10000)
            time.sleep(2)
            print(f"  [OK] ログイン成功: {page.url}")

            # ダークモードに切り替え
            print("\n[4/8] ダークモードに切り替え中...")
            try:
                # ThemeToggleボタンを探してクリック
                theme_toggle = page.locator('button:has(i.mdi-weather-night), button:has(i.mdi-weather-sunny)').first
                current_theme = page.evaluate('''() => {
                    return document.documentElement.classList.contains('dark') ||
                           localStorage.getItem('theme') === 'dark' ? 'dark' : 'light'
                }''')
                print(f"  現在のテーマ: {current_theme}")

                if current_theme != 'dark':
                    theme_toggle.click()
                    time.sleep(1)
                    print("  [OK] ダークモードに切り替えました")
                else:
                    print("  [OK] 既にダークモードです")
            except Exception as e:
                print(f"  [WARNING] テーマ切り替えエラー: {e}")

            # 設備カードが表示されるまで待機
            print("\n[5/8] 設備カードの読み込み待機中...")
            page.wait_for_selector('.glass-card', timeout=10000)
            print("  [OK] 設備カード表示")

            # スクリーンショット1: ツールチップなし
            screenshot_path_1 = Path(__file__).parent / 'tooltip_test_no_hover.png'
            page.screenshot(path=str(screenshot_path_1), full_page=True)
            print(f"  [OK] スクリーンショット保存: {screenshot_path_1}")

            # 最初の設備カードの「監視」ボタンを取得
            print("\n[6/8] ツールチップ表示テスト中...")
            monitor_button = page.locator('button:has-text("監視")').first

            # ボタンにマウスホバー
            monitor_button.hover()
            time.sleep(1.5)  # ツールチップ表示を待つ

            # スクリーンショット2: ツールチップ表示中
            screenshot_path_2 = Path(__file__).parent / 'tooltip_test_hover.png'
            page.screenshot(path=str(screenshot_path_2), full_page=True)
            print(f"  [OK] スクリーンショット保存: {screenshot_path_2}")

            # ツールチップ要素のスタイルを取得
            print("\n[7/8] ツールチップのスタイルを確認中...")
            tooltip_info = page.evaluate('''() => {
                const tooltip = document.querySelector('.v-overlay__content, .v-tooltip__content, .tooltip-custom');
                if (tooltip) {
                    const styles = window.getComputedStyle(tooltip);
                    return {
                        backgroundColor: styles.backgroundColor,
                        color: styles.color,
                        opacity: styles.opacity,
                        display: styles.display,
                        visibility: styles.visibility,
                        innerText: tooltip.innerText
                    };
                }
                return null;
            }''')

            if tooltip_info:
                print("  [OK] ツールチップ要素が見つかりました:")
                print(f"    背景色: {tooltip_info.get('backgroundColor')}")
                print(f"    文字色: {tooltip_info.get('color')}")
                print(f"    不透明度: {tooltip_info.get('opacity')}")
                print(f"    表示: {tooltip_info.get('display')}")
                print(f"    可視性: {tooltip_info.get('visibility')}")
                print(f"    テキスト: {tooltip_info.get('innerText')}")
            else:
                print("  [WARNING] ツールチップ要素が見つかりません")

            # 「ログ」ボタンでもテスト
            print("\n[8/8] ログボタンのツールチップテスト中...")
            log_button = page.locator('button:has-text("ログ")').first
            log_button.hover()
            time.sleep(1.5)

            screenshot_path_3 = Path(__file__).parent / 'tooltip_test_log.png'
            page.screenshot(path=str(screenshot_path_3), full_page=True)
            print(f"  [OK] スクリーンショット保存: {screenshot_path_3}")

            print("\n" + "=" * 70)
            print("  Test Results")
            print("=" * 70)
            print(f"\n[SUCCESS] ツールチップテスト完了")
            print(f"\nスクリーンショット:")
            print(f"  1. ホバーなし: {screenshot_path_1}")
            print(f"  2. 監視ボタン: {screenshot_path_2}")
            print(f"  3. ログボタン: {screenshot_path_3}")

            if tooltip_info:
                print(f"\nツールチップの見え方を確認してください:")
                print(f"  - 背景が濃いグレー（#424242付近）になっているか")
                print(f"  - 文字が白色（#ffffff）になっているか")

            print("\nブラウザは5秒後に自動的に閉じます...")
            time.sleep(5)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] エラーが発生しました: {e}")
            try:
                screenshot_path = Path(__file__).parent / 'tooltip_test_error.png'
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
    success = test_tooltip()
    sys.exit(0 if success else 1)
