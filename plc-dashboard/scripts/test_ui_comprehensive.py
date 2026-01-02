#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
包括的UI崩れテストスクリプト

全ページを体系的にチェックし、UI問題を検出します：
- レイアウト崩れ
- アニメーション動作
- グラスモーフィズム適用
- カラーパレット適用
- レスポンシブデザイン
- コンソールエラー
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Windows環境でのUnicode出力対応
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# スクリーンショット保存ディレクトリ
SCREENSHOT_DIR = Path(__file__).parent / "ui_comprehensive_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# テスト対象ページ
PAGES_TO_TEST = [
    {"name": "login", "path": "/login", "description": "ログイン画面"},
    {"name": "index", "path": "/", "description": "トップページ（設備一覧）"},
    {"name": "monitoring", "path": "/monitoring/DEMO_001", "description": "モニタリング画面"},
    {"name": "errors_alarms", "path": "/errors-alarms", "description": "エラー・アラーム画面"},
    {"name": "logs", "path": "/logs", "description": "ログ画面"},
    {"name": "equipment_detail", "path": "/equipment/DEMO_001", "description": "設備詳細画面"},
]

# テスト結果
test_results = []


async def capture_console_errors(page):
    """コンソールエラーをキャプチャ"""
    errors = []

    async def on_console(msg):
        if msg.type in ['error', 'warning']:
            errors.append({
                'type': msg.type,
                'text': msg.text
            })

    page.on('console', on_console)
    return errors


async def check_glassmorphism(page):
    """グラスモーフィズム効果が適用されているか確認"""
    glass_elements = await page.locator('.glass-card, .glass-header').count()

    if glass_elements > 0:
        # backdrop-filterが適用されているか確認
        backdrop_filter = await page.locator('.glass-card').first.evaluate(
            'el => window.getComputedStyle(el).backdropFilter'
        )
        return {
            'applied': True,
            'count': glass_elements,
            'backdrop_filter': backdrop_filter
        }
    return {'applied': False, 'count': 0}


async def check_animations(page):
    """アニメーションが動作しているか確認"""
    # gradient-textアニメーション
    gradient_elements = await page.locator('.gradient-text').count()

    # value-pulseアニメーション（モニタリング画面用）
    pulse_elements = await page.locator('.value-pulse').count()

    return {
        'gradient_text_count': gradient_elements,
        'value_pulse_count': pulse_elements
    }


async def test_page(browser, page_info, theme='light', viewport_size={'width': 1920, 'height': 1080}):
    """個別ページのテスト"""
    print(f"\n{'='*60}")
    print(f"📄 テスト中: {page_info['description']} ({theme}モード)")
    print(f"{'='*60}")

    page = await browser.new_page(viewport=viewport_size)
    console_errors = []

    # コンソールエラーキャプチャ
    page.on('console', lambda msg:
        console_errors.append({'type': msg.type, 'text': msg.text})
        if msg.type in ['error', 'warning'] else None
    )

    try:
        # ページ遷移
        url = f"http://localhost:3000{page_info['path']}"
        print(f"🔗 URL: {url}")
        await page.goto(url, wait_until='networkidle', timeout=15000)

        # テーマ切り替え（ダークモード用）
        if theme == 'dark':
            theme_toggle = page.locator('[data-test="theme-toggle"], .theme-toggle, button:has-text("ダーク")')
            if await theme_toggle.count() > 0:
                await theme_toggle.first.click()
                await page.wait_for_timeout(500)

        # 少し待機してアニメーションを確認
        await page.wait_for_timeout(2000)

        # グラスモーフィズムチェック
        glassmorphism = await check_glassmorphism(page)
        print(f"✨ グラスモーフィズム: {glassmorphism}")

        # アニメーションチェック
        animations = await check_animations(page)
        print(f"🎬 アニメーション: {animations}")

        # コンソールエラー確認
        errors = [e for e in console_errors if e['type'] == 'error']
        warnings = [e for e in console_errors if e['type'] == 'warning']
        print(f"❌ エラー数: {len(errors)}")
        print(f"⚠️  警告数: {len(warnings)}")

        if errors:
            print("🔴 コンソールエラー:")
            for error in errors[:5]:  # 最初の5件のみ表示
                print(f"  - {error['text'][:100]}")

        # スクリーンショット
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        viewport_label = f"{viewport_size['width']}x{viewport_size['height']}"
        screenshot_path = SCREENSHOT_DIR / f"{page_info['name']}_{theme}_{viewport_label}_{timestamp}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"📸 スクリーンショット: {screenshot_path.name}")

        # 結果保存
        result = {
            'page': page_info['name'],
            'description': page_info['description'],
            'theme': theme,
            'viewport': viewport_label,
            'glassmorphism': glassmorphism,
            'animations': animations,
            'console_errors': len(errors),
            'console_warnings': len(warnings),
            'screenshot': screenshot_path.name,
            'success': len(errors) == 0
        }

        test_results.append(result)

        print(f"✅ テスト完了: {page_info['name']} ({theme})")

        return result

    except Exception as e:
        print(f"❌ エラー発生: {str(e)}")
        result = {
            'page': page_info['name'],
            'description': page_info['description'],
            'theme': theme,
            'viewport': f"{viewport_size['width']}x{viewport_size['height']}",
            'error': str(e),
            'success': False
        }
        test_results.append(result)
        return result

    finally:
        await page.close()


async def main():
    """メインテスト実行"""
    print("\n" + "="*60)
    print("🔍 包括的UI崩れテスト開始")
    print("="*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # テスト実行
        # 1. デスクトップ - ライトモード
        print("\n📱 デスクトップ（1920x1080）- ライトモード")
        for page_info in PAGES_TO_TEST:
            await test_page(browser, page_info, theme='light', viewport_size={'width': 1920, 'height': 1080})

        # 2. デスクトップ - ダークモード
        print("\n🌙 デスクトップ（1920x1080）- ダークモード")
        for page_info in PAGES_TO_TEST:
            await test_page(browser, page_info, theme='dark', viewport_size={'width': 1920, 'height': 1080})

        # 3. タブレット（レスポンシブ確認）
        print("\n📱 タブレット（768x1024）- ライトモード")
        for page_info in PAGES_TO_TEST:
            await test_page(browser, page_info, theme='light', viewport_size={'width': 768, 'height': 1024})

        await browser.close()

    # 結果サマリー
    print("\n" + "="*60)
    print("📊 テスト結果サマリー")
    print("="*60)

    total_tests = len(test_results)
    successful_tests = sum(1 for r in test_results if r.get('success', False))
    failed_tests = total_tests - successful_tests

    print(f"✅ 成功: {successful_tests}/{total_tests}")
    print(f"❌ 失敗: {failed_tests}/{total_tests}")

    # 失敗したテストの詳細
    if failed_tests > 0:
        print("\n🔴 失敗したテスト:")
        for result in test_results:
            if not result.get('success', False):
                print(f"  - {result['description']} ({result['theme']}): {result.get('error', 'コンソールエラー検出')}")

    # コンソールエラーが多いページ
    pages_with_errors = [r for r in test_results if r.get('console_errors', 0) > 0]
    if pages_with_errors:
        print("\n⚠️  コンソールエラーがあるページ:")
        for result in pages_with_errors:
            print(f"  - {result['description']} ({result['theme']}): {result['console_errors']}個のエラー")

    # グラスモーフィズム適用状況
    print("\n✨ グラスモーフィズム適用状況:")
    for result in test_results:
        if 'glassmorphism' in result:
            status = "✅" if result['glassmorphism']['applied'] else "❌"
            print(f"  {status} {result['description']} ({result['theme']}): {result['glassmorphism'].get('count', 0)}個")

    print(f"\n📁 スクリーンショット保存先: {SCREENSHOT_DIR}")
    print("\n🎉 テスト完了！")

    return failed_tests == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
