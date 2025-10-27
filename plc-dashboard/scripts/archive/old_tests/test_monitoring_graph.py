"""
モニタリング画面のグラフ表示テスト（認証付き）
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pathlib import Path
import time

def test_monitoring_with_login(equipment_id="LINE_A_001", username="admin", password="plc-monitor-2025"):
    """モニタリング画面のグラフ表示をテスト（ログイン処理含む）"""
    print(f"\n[INFO] モニタリング画面グラフテスト: {equipment_id}")
    print(f"[INFO] ログインユーザー: {username}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

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

            # ステップ1: ログインページにアクセス
            print("[INFO] ログインページにアクセス中...")
            page.goto("http://localhost:3000/login", wait_until='networkidle', timeout=15000)

            # ステップ2: ログインフォームに入力
            print(f"[INFO] ログイン情報を入力中: {username}")
            page.fill('input[type="text"]', username)
            page.fill('input[type="password"]', password)

            # スクリーンショット: ログインフォーム
            screenshot_login = Path(__file__).parent / 'monitoring_test_01_login.png'
            page.screenshot(path=str(screenshot_login))
            print(f"[INFO] スクリーンショット保存: {screenshot_login}")

            # ステップ3: ログインボタンをクリック
            print("[INFO] ログインボタンをクリック...")
            page.click('button[type="submit"]')

            # ログイン完了を待つ（トップページまたはリダイレクト先）
            print("[INFO] ログイン完了を待機中...")
            time.sleep(2)  # ログイン処理の完了を待つ

            # スクリーンショット: ログイン後
            screenshot_after_login = Path(__file__).parent / 'monitoring_test_02_after_login.png'
            page.screenshot(path=str(screenshot_after_login))
            print(f"[INFO] スクリーンショット保存: {screenshot_after_login}")

            # ステップ4: モニタリング画面に移動
            monitoring_url = f"http://localhost:3000/monitoring/{equipment_id}"
            print(f"[INFO] モニタリング画面にアクセス中: {monitoring_url}")
            page.goto(monitoring_url, wait_until='networkidle', timeout=15000)

            # ステップ5: ページのレンダリングを待つ
            print("[INFO] モニタリング画面のレンダリングを待機中...")
            try:
                # ヘッダー部分を待つ
                page.wait_for_selector('.gradient-text', timeout=10000)
                print("[OK] ヘッダーが表示されました")

                # ステータスカードを待つ
                page.wait_for_selector('.status-card', timeout=10000)
                status_cards = page.locator('.status-card').all()
                print(f"[OK] ステータスカードが表示されました: {len(status_cards)}枚")

                # グラフ（canvas要素）を待つ
                page.wait_for_selector('canvas', timeout=10000)
                canvases = page.locator('canvas').all()
                print(f"[OK] グラフ（canvas）が表示されました: {len(canvases)}個")

                # グラフタイトルを取得
                graph_titles = page.locator('.v-card-title').all_text_contents()
                print(f"[INFO] グラフタイトル一覧:")
                for i, title in enumerate(graph_titles, 1):
                    if title.strip():  # 空白でないタイトルのみ
                        print(f"       {i}. {title.strip()}")

                # スクリーンショット: モニタリング画面全体
                screenshot_monitoring = Path(__file__).parent / f'monitoring_test_03_{equipment_id}_full.png'
                page.screenshot(path=str(screenshot_monitoring), full_page=True)
                print(f"[INFO] スクリーンショット保存（フルページ）: {screenshot_monitoring}")

                # 個別のグラフ領域のスクリーンショット
                for i, canvas in enumerate(canvases, 1):
                    try:
                        screenshot_canvas = Path(__file__).parent / f'monitoring_test_04_{equipment_id}_graph_{i}.png'
                        canvas.screenshot(path=str(screenshot_canvas))
                        print(f"[INFO] グラフ{i}のスクリーンショット保存: {screenshot_canvas}")
                    except Exception as e:
                        print(f"[WARNING] グラフ{i}のスクリーンショット取得失敗: {e}")

                # ステップ6: データカードの値を確認
                print("\n[INFO] データカードの値を確認中...")
                data_values = page.locator('.status-card .text-h3').all_text_contents()
                for i, value in enumerate(data_values, 1):
                    if value.strip() and value.strip() != 'N/A':
                        print(f"       カード{i}: {value.strip()}")

                # ステップ7: 接続ステータスを確認
                connection_status = page.locator('.v-chip').first.text_content()
                print(f"\n[INFO] 接続ステータス: {connection_status}")

            except PlaywrightTimeout:
                print("[ERROR] モニタリング画面のレンダリングがタイムアウトしました")
                screenshot_error = Path(__file__).parent / f'monitoring_test_error_{equipment_id}.png'
                page.screenshot(path=str(screenshot_error), full_page=True)
                print(f"[INFO] エラースクリーンショット保存: {screenshot_error}")
                browser.close()
                return False

            # JavaScriptエラーチェック
            if js_errors or console_errors:
                print("\n[ERROR] JavaScriptエラーが検出されました:")
                for error in js_errors:
                    print(f"  - Page Error: {error}")
                for error in console_errors:
                    print(f"  - Console Error: {error}")
                browser.close()
                return False

            print("\n[OK] JavaScriptエラーなし")
            browser.close()
            return True

        except Exception as e:
            print(f"\n[ERROR] テストエラー: {e}")
            try:
                screenshot_exception = Path(__file__).parent / f'monitoring_test_exception_{equipment_id}.png'
                page.screenshot(path=str(screenshot_exception), full_page=True)
                print(f"[INFO] 例外発生時スクリーンショット: {screenshot_exception}")
            except:
                pass
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  モニタリング画面グラフ表示テスト")
    print("="*70)

    success = test_monitoring_with_login("LINE_A_001")

    print("\n" + "="*70)
    if success:
        print("  [SUCCESS] モニタリング画面グラフテスト成功!")
        print("\n  確認事項:")
        print("    - ログインが正常に完了")
        print("    - ステータスカードが表示")
        print("    - グラフ（canvas）が表示")
        print("    - JavaScriptエラーなし")
    else:
        print("  [FAILED] モニタリング画面グラフテスト失敗")
    print("="*70 + "\n")

    exit(0 if success else 1)
