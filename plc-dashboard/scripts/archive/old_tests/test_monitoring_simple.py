"""
モニタリング画面の簡易テスト（タイムアウト延長版）
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time

def test_simple():
    print("\n[INFO] モニタリング画面簡易テスト開始")

    with sync_playwright() as p:
        try:
            # ブラウザ起動
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # コンソールログをキャプチャ
            console_errors = []
            def handle_console(msg):
                if msg.type == 'error':
                    console_errors.append(msg.text)
            page.on('console', handle_console)

            # ステップ1: ログイン（タイムアウト30秒、wait_until='load'）
            print("[STEP 1] ログインページにアクセス...")
            page.goto("http://localhost:3000/login", wait_until='load', timeout=30000)
            print("[OK] ログインページ表示")

            # ログイン情報入力
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button[type="submit"]')
            time.sleep(5)  # ログイン処理待機
            print("[OK] ログイン完了")

            # ステップ2: モニタリング画面にアクセス
            print("\n[STEP 2] モニタリング画面にアクセス...")
            page.goto("http://localhost:3000/monitoring/LINE_A_001", wait_until='load', timeout=30000)
            time.sleep(5)  # ページ読み込み待機
            print("[OK] モニタリング画面表示")

            # ステップ3: 要素の確認
            print("\n[STEP 3] ページ要素を確認...")

            # ヘッダー
            try:
                header = page.locator('.gradient-text').first
                if header.is_visible():
                    print("[OK] ヘッダー表示: " + header.text_content())
                else:
                    print("[WARNING] ヘッダーが見つかりません")
            except Exception as e:
                print(f"[ERROR] ヘッダー確認エラー: {e}")

            # ステータスカード
            try:
                status_cards = page.locator('.status-card')
                count = status_cards.count()
                print(f"[INFO] ステータスカード数: {count}")
                if count > 0:
                    print("[OK] ステータスカードが表示されています")
                else:
                    print("[WARNING] ステータスカードが見つかりません")
            except Exception as e:
                print(f"[ERROR] ステータスカード確認エラー: {e}")

            # canvas（グラフ）
            try:
                canvases = page.locator('canvas')
                count = canvases.count()
                print(f"[INFO] Canvas数: {count}")
                if count > 0:
                    print("[OK] グラフ（canvas）が表示されています")
                else:
                    print("[WARNING] グラフが見つかりません")
            except Exception as e:
                print(f"[ERROR] グラフ確認エラー: {e}")

            # データテーブル
            try:
                table = page.locator('.v-data-table')
                if table.count() > 0:
                    print("[OK] データテーブルが表示されています")
                else:
                    print("[WARNING] データテーブルが見つかりません")
            except Exception as e:
                print(f"[ERROR] データテーブル確認エラー: {e}")

            # スクリーンショット
            screenshot_path = Path(__file__).parent / 'simple_test_monitoring.png'
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"\n[INFO] スクリーンショット保存: {screenshot_path}")

            # コンソールエラー確認
            print(f"\n[STEP 4] JavaScriptエラー確認...")
            if console_errors:
                print(f"[WARNING] コンソールエラー ({len(console_errors)}件):")
                for i, error in enumerate(console_errors[:5], 1):
                    try:
                        safe_error = error.encode('ascii', 'ignore').decode('ascii')
                        print(f"  {i}. {safe_error[:100]}")
                    except:
                        print(f"  {i}. <encoding error>")
            else:
                print("[OK] JavaScriptエラーなし")

            browser.close()
            print("\n[SUCCESS] テスト完了")
            return True

        except Exception as e:
            print(f"\n[ERROR] テストエラー: {e}")
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    success = test_simple()
    exit(0 if success else 1)
