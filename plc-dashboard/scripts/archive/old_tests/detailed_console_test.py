#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""詳細なコンソールログ取得テスト"""

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
            def log_handler(msg):
                try:
                    text = msg.text
                    console_logs.append(f"[{msg.type}] {text}")
                    # リアルタイムで重要なログを表示
                    if 'chart' in text.lower() or 'watch' in text.lower() or 'init' in text.lower():
                        print(f"  → [{msg.type}] {text}")
                except Exception as e:
                    console_logs.append(f"[{msg.type}] <error: {e}>")

            page.on('console', log_handler)

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

            # 15秒待機（初期化とデータ受信を待つ）
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

            # すべてのコンソールログを出力
            print("\n[ALL CONSOLE LOGS]:")
            for log in console_logs:
                try:
                    # ASCIIのみに変換
                    safe_log = ''.join(c if ord(c) < 128 else '?' for c in log)
                    print(safe_log)
                except:
                    print("[LOG ENCODING ERROR]")

            # スクリーンショット
            page.screenshot(path='detailed_console_test.png', full_page=True)
            print("\n[INFO] Screenshot saved: detailed_console_test.png")

            # 結果判定
            print("\n" + "="*60)
            if chart_state['canvasElements'] >= 5:
                print(f"[SUCCESS] {chart_state['canvasElements']} charts are rendered!")
            elif chart_state['canvasElements'] == 0:
                print(f"[FAILURE] No charts rendered")
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
