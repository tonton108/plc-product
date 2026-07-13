"""描画健全性の回帰テスト（E2E）

共通コンポーネント（components/common/*）が実際に描画されることを検証する。
Nuxtの自動インポート名不一致で `Failed to resolve component` が出ると、
要素ごと無視されて画面が空になる「サイレント破損」が過去に発生した（PR #43で修正）。
本テストはその再発を検知するためのガード:

- 設備詳細の「エラー・アラーム」タブ: PLC通信状態 / アラーム履歴 / エラーログ が描画される
- 設備詳細の「インシデント追跡」タブ: インシデント一覧カードが描画される
- `/errors-alarms` 単体ページ: エラーログカードが描画される
- 上記操作中に `Failed to resolve component` 警告・ページ例外が一切出ない

ロケールは ja-JP に固定する（CIの既定ブラウザは en でUI文言が英語になるため）。
認証情報・設備IDは環境変数で上書き可能（CI: admin/plc-monitor-2025, LINE_A_001）。
"""
import os
import sys
import io
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.environ.get('BASE_URL', 'http://localhost:3000')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'plc-monitor-2025')
EQUIPMENT_ID = os.environ.get('EQUIPMENT_ID', 'LINE_A_001')
IS_CI = os.environ.get('CI', 'false').lower() == 'true'


def main():
    print("=" * 70)
    print("  Render Health Regression Test (common components)")
    print(f"  base={BASE} equipment={EQUIPMENT_ID}")
    print("=" * 70)

    failures = []
    resolve_warnings = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=IS_CI)
        # ja-JP固定でUI文言を日本語に揃える（CIの既定enだと文言が変わりセレクタが崩れる）
        context = browser.new_context(locale='ja-JP')
        page = context.new_page()

        def on_console(msg):
            if msg.type == 'warning' and 'resolve component' in msg.text.lower():
                resolve_warnings.append(msg.text.split('\n')[0])
        page.on('console', on_console)
        page.on('pageerror', lambda e: page_errors.append(str(e)))

        def check(label, cond):
            mark = "OK" if cond else "FAIL"
            print(f"  [{mark}] {label}")
            if not cond:
                failures.append(label)

        try:
            # --- ログイン ---
            print("\n[1] login")
            page.goto(f"{BASE}/login", timeout=20000)
            page.fill('input[type="text"]', ADMIN_USER)
            page.fill('input[type="password"]', ADMIN_PASS)
            page.click('button[type="submit"]')
            page.wait_for_function('window.location.pathname !== "/login"', timeout=15000)
            time.sleep(2)
            check("ログイン成功", page.url.rstrip('/').endswith(BASE.rstrip('/')) or '/login' not in page.url)

            # --- 設備詳細: エラー・アラームタブ ---
            print("\n[2] equipment detail -> errors/alarms tab")
            page.goto(f"{BASE}/equipment/{EQUIPMENT_ID}", timeout=20000)
            page.wait_for_selector('.v-tab', timeout=15000)
            page.click('.v-tab:has-text("エラー・アラーム")')
            time.sleep(2)
            check("PLC通信状態カード描画（PLCStatusCards）",
                  page.locator('text=PLC通信状態').count() >= 1)
            check("アラーム履歴カード描画（AlarmHistoryTable）",
                  page.locator('text=アラーム履歴').count() >= 1)
            check("エラーログカード描画（ErrorLogTable）",
                  page.locator('text=エラーログ').count() >= 1)

            # --- 設備詳細: インシデント追跡タブ ---
            print("\n[3] equipment detail -> incidents tab")
            page.click('.v-tab:has-text("インシデント追跡")')
            time.sleep(2)
            check("インシデント一覧カード描画（IncidentTable）",
                  page.locator('.v-card-title:has-text("インシデント追跡")').count() >= 1)

            # --- /errors-alarms 単体ページ ---
            print("\n[4] /errors-alarms standalone page")
            page.goto(f"{BASE}/errors-alarms", timeout=20000)
            time.sleep(2)
            try:
                page.click('div.v-select', timeout=5000)
                time.sleep(1)
                page.locator('.v-list-item').first.click(timeout=5000)
                time.sleep(2)
            except PlaywrightTimeout:
                print("    (設備選択をスキップ: セレクタ未検出)")
            check("errors-alarmsページでエラーログ描画",
                  page.locator('text=エラーログ').count() >= 1)

        except Exception as e:
            import traceback
            traceback.print_exc()
            failures.append(f"例外: {e}")
        finally:
            context.close()
            browser.close()

    # --- 判定 ---
    print("\n" + "=" * 70)
    if resolve_warnings:
        print(f"  [FAIL] Failed to resolve component 警告 {len(resolve_warnings)}件:")
        for w in sorted(set(resolve_warnings)):
            print(f"        {w}")
        failures.append("resolve警告あり")
    else:
        print("  [OK] Failed to resolve component 警告なし")
    if page_errors:
        print(f"  [FAIL] ページ例外 {len(page_errors)}件:")
        for e in page_errors[:5]:
            print(f"        {e}")
        failures.append("ページ例外あり")
    else:
        print("  [OK] ページ例外なし")

    if failures:
        print(f"\n[RESULT] FAIL ({len(failures)}件): {failures}")
        sys.exit(1)
    print("\n[RESULT] PASS")


if __name__ == "__main__":
    main()
