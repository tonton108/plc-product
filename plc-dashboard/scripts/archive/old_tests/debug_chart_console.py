#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""コンソールエラー詳細確認テスト"""

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

            # すべてのコンソールログをキャプチャ
            console_logs = []
            errors = []

            def console_handler(msg):
                try:
                    text = msg.text
                    log_entry = f"[{msg.type}] {text}"
                    console_logs.append(log_entry)

                    if msg.type in ['error', 'warning']:
                        errors.append(log_entry)
                        print(f"⚠️ {log_entry}")
                except Exception as e:
                    print(f"[ERROR] Failed to capture console: {e}")

            page.on('console', console_handler)

            # ページエラーもキャプチャ
            page.on('pageerror', lambda exc: print(f"🔴 PAGE ERROR: {exc}"))

            # ログイン
            print("\n[INFO] Logging in...")
            page.goto('http://localhost:3000', timeout=30000)
            time.sleep(2)
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            time.sleep(3)

            # モニタリングページ
            print("[INFO] Navigating to monitoring page...")
            page.goto('http://localhost:3000/monitoring/LINE_A_001', timeout=30000)

            # 15秒待機（データ受信とチャート初期化を待つ）
            print("[INFO] Waiting 15 seconds for data and chart initialization...")
            time.sleep(15)

            # 状態確認
            chart_state = page.evaluate("""() => {
                const chartConfigs = document.querySelectorAll('.chart-container');
                const canvasElements = document.querySelectorAll('canvas');
                const vIfElements = document.querySelectorAll('[v-if]');

                return {
                    chartContainers: chartConfigs.length,
                    canvasElements: canvasElements.length,
                    vIfElements: vIfElements.length,
                    firstChartHTML: chartConfigs[0]?.innerHTML.substring(0, 200) || 'N/A'
                };
            }""")

            print(f"\n{'='*60}")
            print(f"[STATE] Chart containers: {chart_state['chartContainers']}")
            print(f"[STATE] Canvas elements: {chart_state['canvasElements']}")
            print(f"[STATE] First chart HTML: {chart_state['firstChartHTML']}")
            print(f"{'='*60}")

            # エラーログを表示
            print(f"\n[ERRORS] {len(errors)} errors/warnings found:")
            for error in errors[-20:]:
                print(f"  {error}")

            # 最近のコンソールログを表示
            print(f"\n[LOGS] Recent console logs ({len(console_logs)} total):")
            for log in console_logs[-30:]:
                print(f"  {log}")

            # スクリーンショット
            page.screenshot(path='debug_chart_console.png', full_page=True)
            print("\n[INFO] Screenshot saved: debug_chart_console.png")

            print("\n[INFO] Browser will stay open for 15 seconds for manual inspection...")
            time.sleep(15)
            browser.close()

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_chart()
