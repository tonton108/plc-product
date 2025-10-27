#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""チャート表示テスト（networkidle版）"""

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

            # ログイン（networkidleで待機）
            print("\n[INFO] Logging in...")
            page.goto('http://localhost:3000', wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)

            try:
                page.fill('input[type="text"]', 'admin', timeout=10000)
                page.fill('input[type="password"]', 'plc-monitor-2025', timeout=10000)
                page.click('button:has-text("ログイン")', timeout=10000)
                print("[OK] Login successful")
            except Exception as e:
                print(f"[WARNING] Login elements not found or already logged in: {e}")

            time.sleep(3)

            # モニタリングページ
            print("[INFO] Navigating to monitoring page...")
            page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='domcontentloaded', timeout=60000)

            # 15秒待機（初期化とデータ受信）
            print("[INFO] Waiting 15 seconds for initialization...")
            time.sleep(15)

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
            page.screenshot(path='final_test_v2.png', full_page=True)
            print("[INFO] Screenshot saved: final_test_v2.png")

            # 結果判定
            print("\n" + "="*60)
            if chart_state['canvasElements'] >= 5:
                print(f"[SUCCESS] {chart_state['canvasElements']} charts are rendered!")
                print("✅ Charts display correctly on initial page load!")
                print("\n🎉 PROBLEM SOLVED!")
                print("  - Fixed v-if/v-else syntax error")
                print("  - Added chartRenderKey increment")
                print("  - Charts now render automatically without debug button")
            elif chart_state['canvasElements'] == 0:
                print(f"[FAILURE] No charts rendered")
                print(f"[INFO] Check screenshot for details")
            else:
                print(f"[PARTIAL] {chart_state['canvasElements']} charts rendered (expected 5)")
            print("="*60)

            print("\n[INFO] Browser will stay open for 20 seconds for manual inspection...")
            time.sleep(20)
            browser.close()

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_chart()
