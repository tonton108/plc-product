#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""chartConfigsの状態を詳細に確認"""

import sys
import time
import json

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

            # 10秒待機
            print("[INFO] Waiting 10 seconds...")
            time.sleep(10)

            # Vue devtools経由でchartConfigsの状態を確認
            chart_info = page.evaluate("""() => {
                // グローバルに公開されているVueインスタンスを探す
                const app = document.querySelector('#__nuxt').__vue_app__;
                if (!app) return { error: 'Vue app not found' };

                // chartConfigsの状態を取得（簡易的な方法）
                const chartContainers = document.querySelectorAll('.chart-container');
                const results = [];

                chartContainers.forEach((container, index) => {
                    const chartDiv = container.querySelector('div[class*="d-flex"]');
                    const canvas = container.querySelector('canvas');
                    results.push({
                        index: index,
                        hasCanvas: !!canvas,
                        hasPlaceholder: !!chartDiv,
                        innerHTML: container.innerHTML.substring(0, 300)
                    });
                });

                return {
                    chartCount: chartContainers.length,
                    charts: results
                };
            }""")

            print(f"\n{'='*60}")
            print(f"[INFO] Chart count: {chart_info.get('chartCount', 0)}")
            print(f"{'='*60}\n")

            for chart in chart_info.get('charts', []):
                print(f"Chart {chart['index']}:")
                print(f"  - Has Canvas: {chart['hasCanvas']}")
                print(f"  - Has Placeholder: {chart['hasPlaceholder']}")
                print(f"  - HTML preview: {chart['innerHTML'][:150]}...")
                print()

            # Vue Devtoolsがあれば使う（なければスキップ）
            try:
                vue_data = page.evaluate("""() => {
                    // __VUE_DEVTOOLS_GLOBAL_HOOK__ 経由でデータを取得
                    if (window.__VUE_DEVTOOLS_GLOBAL_HOOK__) {
                        return { devtools: true };
                    }
                    return { devtools: false };
                }""")
                print(f"[INFO] Vue Devtools available: {vue_data.get('devtools', False)}")
            except:
                print("[INFO] Vue Devtools not available")

            # スクリーンショット
            page.screenshot(path='inspect_chartconfigs.png', full_page=True)
            print("\n[INFO] Screenshot saved: inspect_chartconfigs.png")

            print("\n[INFO] Browser will stay open for 15 seconds for manual inspection...")
            print("[INFO] Please open browser console and check:")
            print("  - chartConfigs variable")
            print("  - chart.data, chart.datasets, chart.options")
            time.sleep(15)
            browser.close()

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_chart()
