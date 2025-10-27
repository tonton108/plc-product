#!/usr/bin/env python3
"""グラフ表示の詳細テスト"""

import asyncio
from playwright.async_api import async_playwright
import sys

async def test_chart_display():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # コンソールログをキャプチャ
        console_messages = []
        page.on('console', lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

        # エラーをキャプチャ
        page_errors = []
        page.on('pageerror', lambda exc: page_errors.append(str(exc)))

        try:
            print("🌐 http://localhost:3000 にアクセス中...")
            await page.goto('http://localhost:3000', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)

            # モニタリングページに遷移
            print("📊 モニタリングページに遷移中...")
            await page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(5000)

            # ページのタイトルを確認
            title = await page.title()
            print(f"✅ ページタイトル: {title}")

            # グラフコンテナの数を確認
            chart_containers = await page.query_selector_all('.chart-container')
            print(f"📊 グラフコンテナ数: {len(chart_containers)}")

            # Canvasエレメントの数を確認
            canvases = await page.query_selector_all('canvas')
            print(f"🎨 Canvas要素数: {len(canvases)}")

            # データ待機中メッセージの確認
            waiting_messages = await page.query_selector_all('text=データ待機中...')
            print(f"⏳ 「データ待機中」メッセージ数: {len(waiting_messages)}")

            # chartConfigsの状態を確認
            chart_configs_count = await page.evaluate('''() => {
                // Vueコンポーネントのデータにアクセスを試みる
                return document.querySelectorAll('.chart-container').length;
            }''')
            print(f"🔍 JavaScript経由のチャートコンテナ数: {chart_configs_count}")

            # スクリーンショット
            screenshot_path = 'test_chart_display.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 スクリーンショット保存: {screenshot_path}")

            # コンソールログを表示（関連するもののみ）
            print("\n📝 コンソールログ（チャート関連）:")
            chart_logs = [msg for msg in console_messages if 'チャート' in msg or 'chart' in msg.lower() or 'plc' in msg.lower()]
            for msg in chart_logs[:20]:
                print(f"  {msg}")

            # エラーを表示
            if page_errors:
                print("\n❌ ページエラー:")
                for error in page_errors:
                    print(f"  {error}")
            else:
                print("\n✅ ページエラーなし")

            # 最近のコンソールログを表示
            print("\n📝 最近のコンソールログ（最新20件）:")
            for msg in console_messages[-20:]:
                print(f"  {msg}")

        except Exception as e:
            print(f"❌ テスト中にエラー: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(test_chart_display())
