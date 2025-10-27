"""
モニタリング画面の詳細調査スクリプト
DOM要素、JavaScriptの状態、コンソールログを詳しく確認します
"""

import sys
import json
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwrightがインストールされていません")
    sys.exit(1)

def test_monitoring_detailed(equipment_id="LINE_A_001"):
    """モニタリング画面を詳細調査"""
    print(f"=== モニタリング画面詳細調査: {equipment_id} ===\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        console_logs = []
        def handle_console(msg):
            try:
                log_text = f"[{msg.type}] {msg.text}"
                console_logs.append(log_text)
                print(f"  {log_text}")
            except Exception:
                pass  # Unicode encoding error

        page.on('console', handle_console)

        try:
            print("1. Login...")
            page.goto("http://localhost:3000/", wait_until='networkidle', timeout=30000)
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            page.wait_for_timeout(2000)

            url = f"http://localhost:3000/monitoring/{equipment_id}"
            print(f"\n2. Open monitoring page: {url}")
            page.goto(url, wait_until='networkidle', timeout=30000)

            print("\n3. Wait 15 seconds...")
            page.wait_for_timeout(15000)

            print("\n4. Check chart data via JavaScript...")
            chart_status = page.evaluate("""
                () => {
                    const canvases = document.querySelectorAll('canvas');
                    const chartCards = document.querySelectorAll('.chart-container');
                    const waitingMessages = document.querySelectorAll('.chart-container .text-h6');

                    return {
                        canvasCount: canvases.length,
                        chartCardCount: chartCards.length,
                        waitingMessageCount: waitingMessages.length,
                        waitingMessages: Array.from(waitingMessages).map(el => el.textContent)
                    };
                }
            """)

            print("\n=== Chart Status ===")
            print(f"  Canvas elements: {chart_status['canvasCount']}")
            print(f"  Chart cards: {chart_status['chartCardCount']}")
            print(f"  Waiting messages: {chart_status['waitingMessageCount']}")
            if chart_status['waitingMessages']:
                for msg in chart_status['waitingMessages']:
                    print(f"    - {msg}")

            screenshot_path = Path(__file__).parent / f'monitoring_{equipment_id}_detailed.png'
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"\n5. Screenshot saved: {screenshot_path}")

            print("\n=== Console Logs (last 10) ===")
            for log in console_logs[-10:]:
                print(f"  {log}")

            print("\nBrowser will stay open for 60 seconds for manual inspection...")
            page.wait_for_timeout(60000)

            browser.close()

        except Exception as e:
            print(f"\nError: {e}")
            browser.close()

if __name__ == '__main__':
    test_monitoring_detailed()
