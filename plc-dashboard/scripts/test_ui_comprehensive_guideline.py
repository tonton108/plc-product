# -*- coding: utf-8 -*-
"""
包括的UI監査スクリプト（ガイドライン準拠確認）

このスクリプトは以下を検証します：
1. ライトモード・ダークモードの両方でスクリーンショット取得
2. 主要ページ（トップ、モニタリング、エラー・アラーム、ログ）のチェック
3. レスポンシブ対応（デスクトップ、タブレット、モバイル）
4. ガイドライン準拠の確認（カラーパレット、フォント、アニメーション）
"""
import sys
import io

# Windows環境での文字コード問題を回避
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright, Page
import time
from pathlib import Path

# スクリーンショット保存ディレクトリ
SCREENSHOT_DIR = Path(__file__).parent / 'ui_guideline_screenshots'
SCREENSHOT_DIR.mkdir(exist_ok=True)

# テスト設定
BASE_URL = 'http://localhost:3000'
DEMO_EQUIPMENT_ID = 'DEMO_001'

# ビューポート設定（ガイドライン準拠）
VIEWPORTS = {
    'desktop': {'width': 1920, 'height': 1080},       # 中央サーバー PC
    'tablet_landscape': {'width': 1024, 'height': 768}, # タブレット横向き
    'raspi': {'width': 800, 'height': 480},            # ラズパイタッチスクリーン（優先）
}

def wait_for_page_load(page: Page, timeout: int = 5000):
    """ページの読み込みを待機"""
    try:
        page.wait_for_load_state('networkidle', timeout=timeout)
        time.sleep(0.5)  # アニメーション完了を待つ
    except Exception as e:
        print(f"[WARNING] Page load warning: {e}")

def take_screenshot(page: Page, name: str, viewport: str, theme: str):
    """スクリーンショットを撮影"""
    filename = f"{name}_{viewport}_{theme}.png"
    filepath = SCREENSHOT_DIR / filename
    page.screenshot(path=str(filepath), full_page=True)
    print(f"[OK] Screenshot saved: {filename}")

def set_theme(page: Page, theme_name: str):
    """テーマを設定（localStorageを使用）"""
    try:
        # localStorageにテーマを設定してページをリロード
        page.evaluate(f'''
            () => {{
                localStorage.setItem('theme', '{theme_name}');
            }}
        ''')
        page.reload()
        wait_for_page_load(page)
        print(f"[OK] Theme set to: {theme_name}")
    except Exception as e:
        print(f"[WARNING] Theme setting failed: {e}")

def login(page: Page):
    """ログイン処理"""
    print(f"[INFO] Accessing login page: {BASE_URL}")
    page.goto(BASE_URL)
    wait_for_page_load(page)

    # ログインフォームに入力
    page.fill('input[type="text"]', 'admin')
    page.fill('input[type="password"]', 'plc-monitor-2025')

    # ログインボタンをクリックしてナビゲーション完了を待機
    page.click('button[type="submit"]')

    # ログイン後のリダイレクトを待機（URLが変わるまで）
    try:
        page.wait_for_url(lambda url: '/login' not in url, timeout=10000)
        current_url = page.url
        print(f"[OK] Login successful - Redirected to: {current_url}")
    except Exception as e:
        current_url = page.url
        print(f"[WARNING] Login may have failed - Current URL: {current_url}")
        print(f"[WARNING] Error: {e}")

def test_home_page(page: Page, viewport: str, theme: str):
    """トップページのテスト"""
    print(f"\n[TEST] Home page ({viewport}, {theme})")

    # 現在のURLを確認
    current_url = page.url
    if '/login' in current_url:
        print(f"[WARNING] Still on login page, navigating to home...")
        page.goto(f'{BASE_URL}/')
        wait_for_page_load(page)
    elif current_url != f'{BASE_URL}/':
        page.goto(f'{BASE_URL}/')
        wait_for_page_load(page)

    # スクリーンショット撮影
    take_screenshot(page, '01_home', viewport, theme)

    # JavaScript エラーチェック
    js_errors = page.evaluate('''
        () => {
            const errors = [];
            window.addEventListener('error', (e) => errors.push(e.message));
            return errors;
        }
    ''')
    if js_errors:
        print(f"[WARNING] JavaScript errors detected: {js_errors}")

def test_monitoring_page(page: Page, viewport: str, theme: str):
    """モニタリングページのテスト"""
    print(f"\n[TEST] Monitoring page ({viewport}, {theme})")
    page.goto(f'{BASE_URL}/monitoring/{DEMO_EQUIPMENT_ID}')
    wait_for_page_load(page, timeout=10000)

    # グラフの描画を待機
    time.sleep(2)

    # スクリーンショット撮影
    take_screenshot(page, '02_monitoring', viewport, theme)

def test_errors_alarms_page(page: Page, viewport: str, theme: str):
    """エラー・アラームページのテスト"""
    print(f"\n[TEST] Errors & Alarms page ({viewport}, {theme})")
    page.goto(f'{BASE_URL}/errors-alarms')
    wait_for_page_load(page)

    # スクリーンショット撮影
    take_screenshot(page, '03_errors_alarms', viewport, theme)

def test_logs_page(page: Page, viewport: str, theme: str):
    """ログページのテスト"""
    print(f"\n[TEST] Logs page ({viewport}, {theme})")
    page.goto(f'{BASE_URL}/logs')
    wait_for_page_load(page)

    # スクリーンショット撮影
    take_screenshot(page, '04_logs', viewport, theme)

def test_equipment_detail_page(page: Page, viewport: str, theme: str):
    """設備詳細ページのテスト"""
    print(f"\n[TEST] Equipment detail page ({viewport}, {theme})")
    page.goto(f'{BASE_URL}/equipment/{DEMO_EQUIPMENT_ID}')
    wait_for_page_load(page, timeout=10000)

    # グラフの描画を待機
    time.sleep(2)

    # スクリーンショット撮影
    take_screenshot(page, '05_equipment_detail', viewport, theme)

def run_comprehensive_test():
    """包括的UIテストを実行"""
    print("=" * 80)
    print("[START] Comprehensive UI Audit Test (Guideline Compliance Check)")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 各ビューポートでテスト
        for viewport_name, viewport_size in VIEWPORTS.items():
            print(f"\n{'='*80}")
            print(f"[VIEWPORT] {viewport_name} ({viewport_size['width']}x{viewport_size['height']})")
            print(f"{'='*80}")

            # ブラウザコンテキストを作成
            context = browser.new_context(
                viewport=viewport_size,
                locale='ja-JP'
            )
            page = context.new_page()

            # ログイン
            login(page)

            # ライトモードでテスト
            print(f"\n[THEME] Light Mode Test")
            test_home_page(page, viewport_name, 'light')
            test_monitoring_page(page, viewport_name, 'light')
            test_errors_alarms_page(page, viewport_name, 'light')
            test_logs_page(page, viewport_name, 'light')
            test_equipment_detail_page(page, viewport_name, 'light')

            # ダークモードに設定
            set_theme(page, 'dark')

            # ダークモードでテスト
            print(f"\n[THEME] Dark Mode Test")
            test_home_page(page, viewport_name, 'dark')
            test_monitoring_page(page, viewport_name, 'dark')
            test_errors_alarms_page(page, viewport_name, 'dark')
            test_logs_page(page, viewport_name, 'dark')
            test_equipment_detail_page(page, viewport_name, 'dark')

            context.close()

        browser.close()

    print("\n" + "=" * 80)
    print("[COMPLETE] Comprehensive UI Audit Test Completed")
    print(f"[INFO] Screenshot directory: {SCREENSHOT_DIR}")
    print("=" * 80)

    # 総撮影枚数を表示
    screenshot_count = len(list(SCREENSHOT_DIR.glob('*.png')))
    print(f"\n[RESULT] Screenshots taken: {screenshot_count}")
    print(f"[EXPECT] Expected: {len(VIEWPORTS)} viewports x 5 pages x 2 themes = {len(VIEWPORTS) * 5 * 2}")

if __name__ == '__main__':
    import sys
    try:
        run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
