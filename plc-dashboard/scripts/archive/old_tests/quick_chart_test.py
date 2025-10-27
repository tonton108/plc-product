#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""グラフ表示の簡易テスト（ログイン対応）"""

import sys
import time

try:
    from playwright.sync_api import sync_playwright
    print("[OK] Playwright installed")
except ImportError:
    print("[ERROR] Playwright not found")
    print("Install: pip install playwright && playwright install chromium")
    sys.exit(1)

def test_chart():
    with sync_playwright() as p:
        try:
            print("[INFO] Launching browser...")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # コンソールログをキャプチャ
            console_logs = []
            page.on('console', lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

            # ログインページにアクセス
            print("[INFO] Navigating to http://localhost:3000")
            page.goto('http://localhost:3000', wait_until='networkidle', timeout=30000)
            time.sleep(2)

            # ログイン処理（管理者アカウント）
            print("[INFO] Logging in as admin...")
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')

            print("[INFO] Waiting for login to complete...")
            time.sleep(3)

            # モニタリングページに遷移
            print("[INFO] Navigating to monitoring page...")
            page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle', timeout=30000)

            print("[INFO] Waiting 5 seconds for chart initialization...")
            time.sleep(5)

            # グラフコンテナの数を確認
            chart_containers = page.query_selector_all('.chart-container')
            print(f"[RESULT] Chart containers: {len(chart_containers)}")

            # Canvasエレメントの数を確認
            canvases = page.query_selector_all('canvas')
            print(f"[RESULT] Canvas elements: {len(canvases)}")

            # 「データ待機中」メッセージの確認
            waiting_messages = page.query_selector_all('text=データ待機中...')
            print(f"[RESULT] Waiting messages: {len(waiting_messages)}")

            # グラフタイトルを確認
            chart_titles = page.query_selector_all('.v-card-title')
            print(f"[INFO] Found {len(chart_titles)} card titles")

            # スクリーンショット保存
            screenshot_path = 'quick_chart_test.png'
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"[INFO] Screenshot saved: {screenshot_path}")

            # すべてのコンソールログを表示
            print("\n[LOGS] All console logs (last 30):")
            for log in console_logs[-30:]:
                print(f"  {log}")

            # 結果判定
            print("\n" + "="*60)
            if len(canvases) > 0:
                print(f"[SUCCESS] {len(canvases)} charts are displayed!")
            elif len(waiting_messages) > 0:
                print(f"[WARNING] {len(waiting_messages)} charts are waiting for data")
                print("[INFO] This may be normal during initialization")
            elif len(chart_containers) > 0:
                print(f"[INFO] {len(chart_containers)} chart containers found")
                print("[INFO] Charts may be initializing...")
            else:
                print("[ERROR] No charts found")
            print("="*60)

            print("\n[INFO] Keeping browser open for 10 seconds (manual check)...")
            time.sleep(10)

            browser.close()

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_chart()
