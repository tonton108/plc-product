#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""グラフ初期化の詳細テスト"""

import sys
import time
import json

try:
    from playwright.sync_api import sync_playwright
    print("[OK] Playwright installed")
except ImportError:
    print("[ERROR] Playwright not found")
    sys.exit(1)

def test_chart_initialization():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # コンソールログをキャプチャ（UnicodeError回避）
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
            time.sleep(5)

            # JavaScriptでchartConfigsの状態を確認
            print("\n[DEBUG] Checking chartConfigs state...")

            chart_state = page.evaluate("""() => {
                return {
                    chartContainers: document.querySelectorAll('.chart-container').length,
                    canvasElements: document.querySelectorAll('canvas').length,
                    vCardTitles: document.querySelectorAll('.v-card-title').length,
                };
            }""")

            print(f"[STATE] Chart containers: {chart_state['chartContainers']}")
            print(f"[STATE] Canvas elements: {chart_state['canvasElements']}")
            print(f"[STATE] Card titles: {chart_state['vCardTitles']}")

            # コンソールログから初期化関連のログを抽出
            print("\n[LOGS] Initialization logs:")
            init_logs = [log for log in console_logs if any(keyword in log.lower() for keyword in ['chart', 'init', 'config', 'data'])]
            for log in init_logs[-30:]:
                # ASCII範囲外の文字を除去
                safe_log = ''.join(c if ord(c) < 128 else '?' for c in log)
                print(f"  {safe_log}")

            # スクリーンショット
            page.screenshot(path='detailed_chart_test.png', full_page=True)
            print("\n[INFO] Screenshot saved: detailed_chart_test.png")

            # 診断
            print("\n" + "="*60)
            if chart_state['canvasElements'] > 0:
                print(f"[SUCCESS] {chart_state['canvasElements']} charts rendered!")
            else:
                print("[ERROR] No charts rendered")
                print("[DIAGNOSIS]")
                print("  - Chart containers exist but no canvas elements")
                print("  - This suggests chart.data or chart.options are not initialized")
                print("  - Check console logs above for initialization errors")
            print("="*60)

            print("\n[INFO] Browser will close in 10 seconds...")
            time.sleep(10)
            browser.close()

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_chart_initialization()
