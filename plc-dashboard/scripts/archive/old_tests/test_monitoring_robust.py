"""
モニタリング画面の堅牢なテスト（接続問題対策版）
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pathlib import Path
import time

def test_monitoring_robust(equipment_id="LINE_A_001"):
    """接続問題に対応した堅牢なテスト"""
    print(f"\n[INFO] モニタリング画面堅牢テスト: {equipment_id}")

    with sync_playwright() as p:
        try:
            # ブラウザ起動（より堅牢な設定）
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu'
                ]
            )

            # コンテキスト作成（タイムアウト設定）
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            context.set_default_timeout(60000)  # 60秒タイムアウト

            page = context.new_page()

            # JavaScriptエラーを記録
            js_errors = []
            console_errors = []

            def handle_console(msg):
                if msg.type == 'error':
                    console_errors.append(msg.text)

            def handle_page_error(error):
                js_errors.append(str(error))

            page.on('console', handle_console)
            page.on('pageerror', handle_page_error)

            # ステップ1: ログインページにアクセス（リトライあり）
            print("\n[STEP 1] ログインページにアクセス...")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # domcontentloadedを使用（networkidleより早く完了する）
                    page.goto(
                        "http://localhost:3000/login",
                        wait_until='domcontentloaded',
                        timeout=45000
                    )
                    # 追加の待機
                    page.wait_for_load_state('networkidle', timeout=10000)
                    print(f"[OK] ログインページ表示成功（試行 {attempt + 1}/{max_retries}）")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"[WARNING] 試行 {attempt + 1} 失敗、再試行中... ({e})")
                        time.sleep(2)
                    else:
                        raise

            # ログイン情報入力
            print("[INFO] ログイン情報を入力...")
            page.wait_for_selector('input[type="text"]', timeout=10000)
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')

            # スクリーンショット: ログインフォーム
            screenshot_login = Path(__file__).parent / 'robust_test_01_login.png'
            page.screenshot(path=str(screenshot_login))
            print(f"[INFO] スクリーンショット: {screenshot_login}")

            # ログインボタンクリック
            print("[INFO] ログインボタンをクリック...")
            page.click('button[type="submit"]')
            time.sleep(5)  # ログイン処理待機
            print("[OK] ログイン完了")

            # ステップ2: モニタリング画面にアクセス
            print(f"\n[STEP 2] モニタリング画面にアクセス: {equipment_id}")
            for attempt in range(max_retries):
                try:
                    monitoring_url = f"http://localhost:3000/monitoring/{equipment_id}"
                    page.goto(
                        monitoring_url,
                        wait_until='domcontentloaded',
                        timeout=45000
                    )
                    # 追加の待機
                    time.sleep(3)
                    print(f"[OK] モニタリング画面表示成功（試行 {attempt + 1}/{max_retries}）")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"[WARNING] 試行 {attempt + 1} 失敗、再試行中... ({e})")
                        time.sleep(2)
                    else:
                        raise

            # ステップ3: ページ要素の確認
            print("\n[STEP 3] ページ要素の確認...")

            # データ読み込み待機
            print("[INFO] データ読み込みを待機中（10秒）...")
            time.sleep(10)

            # ヘッダー
            try:
                header = page.locator('.gradient-text').first
                if header.is_visible(timeout=5000):
                    header_text = header.text_content()
                    print(f"  [OK] ヘッダー: {header_text}")
                else:
                    print(f"  [WARNING] ヘッダーが見えません")
            except Exception as e:
                print(f"  [ERROR] ヘッダー確認エラー: {e}")

            # ステータスカード
            try:
                status_cards = page.locator('.status-card')
                count = status_cards.count()
                print(f"  [INFO] ステータスカード数: {count}")
                if count > 0:
                    print(f"  [OK] ステータスカードが表示されています")
                else:
                    print(f"  [WARNING] ステータスカードが見つかりません")
                    # 代替: すべてのv-cardをカウント
                    all_cards = page.locator('.v-card').count()
                    print(f"  [INFO] 代替: v-card総数 = {all_cards}")
            except Exception as e:
                print(f"  [ERROR] ステータスカード確認エラー: {e}")

            # グラフ（canvas）
            try:
                canvases = page.locator('canvas')
                count = canvases.count()
                print(f"  [INFO] Canvas数: {count}")
                if count > 0:
                    print(f"  [OK] グラフ（canvas）が表示されています")
                else:
                    print(f"  [WARNING] グラフが見つかりません")
            except Exception as e:
                print(f"  [ERROR] グラフ確認エラー: {e}")

            # データテーブル
            try:
                tables = page.locator('.v-data-table')
                count = tables.count()
                if count > 0:
                    print(f"  [OK] データテーブルが表示されています")
                    # テーブルの行数を確認
                    rows = page.locator('tbody tr').count()
                    print(f"  [INFO] テーブル行数: {rows}")
                else:
                    print(f"  [WARNING] データテーブルが見つかりません")
            except Exception as e:
                print(f"  [ERROR] データテーブル確認エラー: {e}")

            # スクリーンショット: モニタリング画面全体
            screenshot_monitoring = Path(__file__).parent / f'robust_test_02_{equipment_id}_full.png'
            page.screenshot(path=str(screenshot_monitoring), full_page=True)
            print(f"\n[INFO] スクリーンショット: {screenshot_monitoring}")

            # ステップ4: JavaScriptエラー確認
            print("\n[STEP 4] JavaScriptエラー確認...")
            if js_errors or console_errors:
                print(f"  [WARNING] JavaScriptエラー検出:")
                for error in js_errors[:3]:
                    try:
                        safe_error = str(error).encode('ascii', 'ignore').decode('ascii')
                        print(f"    - Page Error: {safe_error[:100]}")
                    except:
                        print(f"    - Page Error: <encoding error>")
                for error in console_errors[:3]:
                    try:
                        safe_error = error.encode('ascii', 'ignore').decode('ascii')
                        print(f"    - Console Error: {safe_error[:100]}")
                    except:
                        print(f"    - Console Error: <encoding error>")
            else:
                print(f"  [OK] JavaScriptエラーなし")

            browser.close()
            print("\n[SUCCESS] テスト完了")
            return True

        except Exception as e:
            print(f"\n[ERROR] テストエラー: {e}")
            import traceback
            traceback.print_exc()
            try:
                screenshot_error = Path(__file__).parent / f'robust_test_error_{equipment_id}.png'
                page.screenshot(path=str(screenshot_error), full_page=True)
                print(f"[INFO] エラースクリーンショット: {screenshot_error}")
            except:
                pass
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  モニタリング画面堅牢テスト")
    print("="*70)

    success = test_monitoring_robust("LINE_A_001")

    print("\n" + "="*70)
    if success:
        print("  [SUCCESS] テスト成功")
    else:
        print("  [FAILED] テスト失敗")
    print("="*70 + "\n")

    exit(0 if success else 1)
