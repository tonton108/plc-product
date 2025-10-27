"""
モニタリング画面のスクリーンショット撮影スクリプト
Playwrightを使ってブラウザでページを開き、グラフの表示を確認します
"""

import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwrightがインストールされていません")
    print("インストールコマンド:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

def test_monitoring_page(equipment_id="LINE_A_001", wait_time=10000):
    """
    モニタリング画面をテスト

    Args:
        equipment_id: 設備ID
        wait_time: ページ読み込み待機時間（ミリ秒）
    """
    print(f"モニタリング画面テスト開始: {equipment_id}")

    with sync_playwright() as p:
        # Chromiumをヘッドレスモードで起動
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # JavaScriptエラーとコンソールログを記録
        js_errors = []
        console_logs = []

        def handle_console(msg):
            console_logs.append(f"[{msg.type}] {msg.text}")
            if msg.type == 'error':
                print(f"  JS Console Error: {msg.text}")

        def handle_page_error(error):
            js_errors.append(str(error))
            print(f"  Page Error: {error}")

        page.on('console', handle_console)
        page.on('pageerror', handle_page_error)

        try:
            # まずトップページにアクセスしてログイン
            print("  ログインページにアクセス中...")
            page.goto("http://localhost:3000/", wait_until='networkidle', timeout=30000)

            # ログイン情報を入力（デフォルトユーザー: admin）
            print("  ログイン情報を入力中...")
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')

            # ログインボタンをクリック
            print("  ログインボタンをクリック...")
            page.click('button:has-text("ログイン")')
            page.wait_for_timeout(2000)

            # モニタリング画面を開く
            url = f"http://localhost:3000/monitoring/{equipment_id}"
            print(f"  モニタリング画面にアクセス中: {url}")
            page.goto(url, wait_until='networkidle', timeout=30000)

            # ページが読み込まれるまで待機
            print(f"  ページ読み込み待機中... ({wait_time}ms)")
            page.wait_for_timeout(wait_time)

            # スクリーンショットを保存
            screenshot_path = Path(__file__).parent / f'monitoring_{equipment_id}_full.png'
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"  スクリーンショット保存: {screenshot_path}")

            # ページタイトルを取得
            title = page.title()
            print(f"  ページタイトル: {title}")

            # Canvasエレメント（Chart.js）を確認
            canvas_elements = page.locator('canvas').count()
            print(f"  検出されたグラフ（canvas要素）: {canvas_elements}個")

            # データカードを確認
            data_cards = page.locator('.v-card').count()
            print(f"  検出されたカード要素: {data_cards}個")

            # JavaScriptエラーチェック
            if js_errors:
                print(f"  警告: JavaScriptエラーが{len(js_errors)}件検出されました:")
                for error in js_errors:
                    print(f"    - {error}")
            else:
                print("  JavaScriptエラーなし")

            # コンソールログの一部を表示
            if console_logs:
                print(f"  コンソールログ（最新5件）:")
                for log in console_logs[-5:]:
                    print(f"    {log}")

            browser.close()

            return {
                'success': len(js_errors) == 0,
                'canvas_count': canvas_elements,
                'card_count': data_cards,
                'screenshot': str(screenshot_path),
                'title': title
            }

        except PlaywrightTimeout as e:
            print(f"  タイムアウトエラー: {e}")
            screenshot_path = Path(__file__).parent / f'monitoring_{equipment_id}_error.png'
            page.screenshot(path=str(screenshot_path))
            print(f"  エラースクリーンショット保存: {screenshot_path}")
            browser.close()
            return {
                'success': False,
                'error': str(e),
                'screenshot': str(screenshot_path)
            }

        except Exception as e:
            print(f"  予期しないエラー: {e}")
            try:
                screenshot_path = Path(__file__).parent / f'monitoring_{equipment_id}_exception.png'
                page.screenshot(path=str(screenshot_path))
                print(f"  例外スクリーンショット保存: {screenshot_path}")
            except:
                pass
            browser.close()
            return {
                'success': False,
                'error': str(e)
            }

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='モニタリング画面スクリーンショットテスト')
    parser.add_argument('--equipment-id', default='LINE_A_001', help='設備ID')
    parser.add_argument('--wait-time', type=int, default=10000, help='待機時間（ミリ秒）')

    args = parser.parse_args()

    result = test_monitoring_page(args.equipment_id, args.wait_time)

    print("\n========================================")
    print("テスト結果")
    print("========================================")
    print(f"成功: {result.get('success', False)}")
    print(f"グラフ数: {result.get('canvas_count', 0)}")
    print(f"カード数: {result.get('card_count', 0)}")
    if 'screenshot' in result:
        print(f"スクリーンショット: {result['screenshot']}")
    print("========================================")

    sys.exit(0 if result.get('success', False) else 1)
