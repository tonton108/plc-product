#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""最終グラフ表示テスト"""

import sys
import time

try:
    from playwright.sync_api import sync_playwright
    print("[OK] Playwright installed")
except ImportError:
    print("[ERROR] Playwright not found")
    sys.exit(1)

def test_chart():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # コンソールログをキャプチャ
            console_logs = []
            def log_handler(msg):
                try:
                    text = msg.text.encode('utf-8', errors='replace').decode('utf-8')
                    console_logs.append(f"[{msg.type}] {text}")
                except:
                    console_logs.append(f"[{msg.type}] <encoding error>")

            page.on('console', log_handler)

            # ログイン
            print("[INFO] Logging in...")
            page.goto('http://localhost:3000', timeout=30000)
            time.sleep(2)
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            time.sleep(3)

            # モニタリングページ
            print("[INFO] Navigating to monitoring page...")
            page.goto('http://localhost:3000/monitoring/LINE_A_001', timeout=30000)

            # 10秒待機（初期化とデータ受信を待つ）
            print("[INFO] Waiting 10 seconds for initialization...")
            time.sleep(10)

            # 状態確認
            chart_state = page.evaluate("""() => {
                return {
                    chartContainers: document.querySelectorAll('.chart-container').length,
                    canvasElements: document.querySelectorAll('canvas').length,
                };
            }""")

            print(f"\n[STATE] Chart containers: {chart_state['chartContainers']}")
            print(f"[STATE] Canvas elements: {chart_state['canvasElements']}")

            # チャート初期化関連ログを抽出
            print("\n[LOGS] Chart initialization logs:")
            init_logs = [log for log in console_logs if 'chart' in log.lower() or 'init' in log.lower()]
            for log in init_logs[-30:]:
                safe_log = ''.join(c if ord(c) < 128 else '?' for c in log)
                print(f"  {safe_log}")

            # スクリーンショット
            page.screenshot(path='final_chart_test.png', full_page=True)
            print("\n[INFO] Screenshot saved: final_chart_test.png")

            # 結果判定
            print("\n" + "="*60)
            if chart_state['canvasElements'] >= 5:
                print(f"[SUCCESS] {chart_state['canvasElements']} charts are rendered!")
            elif chart_state['canvasElements'] == 0:
                print(f"[FAILURE] No charts rendered")
                print(f"[INFO] {chart_state['chartContainers']} containers exist but no canvas elements")
                print("[INFO] Charts are not initializing properly")
            else:
                print(f"[PARTIAL] {chart_state['canvasElements']} charts rendered (expected 5)")
            print("="*60)

            print("\n[INFO] Browser will stay open for 15 seconds for manual inspection...")
            time.sleep(15)
            browser.close()

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_chart()
