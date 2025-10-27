#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ポート3001でのチャートテスト"""

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

            # ログイン
            print("\n[INFO] Logging in (port 3001)...")
            page.goto('http://localhost:3001', timeout=30000)
            time.sleep(2)
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            time.sleep(3)

            # モニタリングページ
            print("[INFO] Navigating to monitoring page...")
            page.goto('http://localhost:3001/monitoring/LINE_A_001', timeout=30000)

            # 10秒待機
            print("[INFO] Waiting 10 seconds for initialization...")
            time.sleep(10)

            # 状態確認
            chart_state = page.evaluate("""() => {
                return {
                    chartContainers: document.querySelectorAll('.chart-container').length,
                    canvasElements: document.querySelectorAll('canvas').length,
                };
            }""")

            print(f"\n{'='*60}")
            print(f"[STATE] Chart containers: {chart_state['chartContainers']}")
            print(f"[STATE] Canvas elements: {chart_state['canvasElements']}")
            print(f"{'='*60}\n")

            # スクリーンショット
            page.screenshot(path='test_port3001.png', full_page=True)
            print("[INFO] Screenshot saved: test_port3001.png")

            # 結果判定
            print("\n" + "="*60)
            if chart_state['canvasElements'] >= 5:
                print(f"[SUCCESS] {chart_state['canvasElements']} charts are rendered!")
                print("✅ Charts are displaying correctly on initial page load!")
            elif chart_state['canvasElements'] == 0:
                print(f"[FAILURE] No charts rendered")
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
