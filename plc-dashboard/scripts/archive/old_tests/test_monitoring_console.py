"""
モニタリング画面のコンソールログを詳細確認
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time

def test_monitoring_console(equipment_id="LINE_A_001"):
    """コンソールログを詳細に確認"""
    print(f"\n[INFO] モニタリング画面コンソールログ確認: {equipment_id}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # すべてのコンソールメッセージを記録
            console_messages = []

            def handle_console(msg):
                text = msg.text
                msg_type = msg.type
                console_messages.append(f"[{msg_type.upper()}] {text}")
                # リアルタイムで表示（エラーと警告のみ）
                if msg_type in ['error', 'warning']:
                    try:
                        # 絵文字を除去
                        safe_text = text.encode('ascii', 'ignore').decode('ascii')
                        print(f"  [{msg_type.upper()}] {safe_text}")
                    except:
                        print(f"  [{msg_type.upper()}] <encoding error>")

            page.on('console', handle_console)

            # ログイン
            print("[STEP 1] ログイン処理...")
            page.goto("http://localhost:3000/login", wait_until='networkidle', timeout=15000)
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button[type="submit"]')
            time.sleep(3)

            # モニタリング画面に移動
            print(f"\n[STEP 2] モニタリング画面にアクセス...")
            page.goto(f"http://localhost:3000/monitoring/{equipment_id}", wait_until='networkidle', timeout=15000)
            time.sleep(5)

            # ページの状態を評価
            print("\n[STEP 3] ページの状態を評価...")

            # JavaScriptで直接データを取得
            page_state = page.evaluate('''() => {
                return {
                    hasMonitoringData: typeof monitoringData !== 'undefined',
                    hasPLCConfigs: typeof plcConfigs !== 'undefined',
                    hasChartConfigs: typeof chartManagement !== 'undefined'
                }
            }''')

            print(f"  monitoringData存在: {page_state.get('hasMonitoringData', False)}")
            print(f"  plcConfigs存在: {page_state.get('hasPLCConfigs', False)}")
            print(f"  chartConfigs存在: {page_state.get('hasChartConfigs', False)}")

            # 要素の数を確認
            status_card_count = page.locator('.status-card').count()
            v_card_count = page.locator('.v-card').count()
            canvas_count = page.locator('canvas').count()

            print(f"\n[STEP 4] DOM要素の確認:")
            print(f"  .status-card: {status_card_count}個")
            print(f"  .v-card: {v_card_count}個")
            print(f"  canvas: {canvas_count}個")

            # スクリーンショット
            screenshot_path = Path(__file__).parent / f'console_test_{equipment_id}.png'
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"\n[INFO] スクリーンショット: {screenshot_path}")

            # コンソールログをすべて出力
            print(f"\n[STEP 5] コンソールログ一覧 ({len(console_messages)}件):")
            for i, msg in enumerate(console_messages[-30:], 1):  # 最新30件
                try:
                    safe_msg = msg.encode('ascii', 'ignore').decode('ascii')
                    print(f"  {i}. {safe_msg[:100]}")
                except:
                    print(f"  {i}. <encoding error>")

            print(f"\n[INFO] 30秒間ブラウザを開いたままにします...")
            time.sleep(30)

            browser.close()
            return True

        except Exception as e:
            print(f"\n[ERROR] エラー: {e}")
            import traceback
            traceback.print_exc()
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    test_monitoring_console("LINE_A_001")
