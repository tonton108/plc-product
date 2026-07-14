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

        # 要素の出現を最大timeoutミリ秒待って真偽を返す。
        # 固定 time.sleep では CI 負荷時に遅延描画（v-window の遅延マウント）を取りこぼし
        # フレーキーになっていたため、明示待機に置き換える。
        def wait_visible(selector, timeout=10000):
            try:
                page.wait_for_selector(selector, state='visible', timeout=timeout)
                return True
            except PlaywrightTimeout:
                return False

        # Vuetifyのv-tabsは、ページ初期化直後の「最初のタブクリック」がコンポーネントの
        # 対話準備完了前だとv-modelに反映されず、対象タブ内容が非アクティブ(display:none)の
        # ままになることがある（本テストのフレーキーの主因。standaloneページのErrorLogTableは
        # 可視なのに詳細タブ側だけ不可視になる現象で確認）。クリック→内容の可視化を待ち、
        # 反映されなければ再クリックする。
        def open_tab(tab_text, content_selector, attempts=3, timeout=8000):
            for _ in range(attempts):
                page.click(f'.v-tab:has-text("{tab_text}")')
                if wait_visible(content_selector, timeout=timeout):
                    return True
            return False

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
            # タブを開いて内容(先頭カード)の可視化を待つ（クリック未反映なら再クリック）。
            opened = open_tab("エラー・アラーム", 'text=PLC通信状態')
            check("PLC通信状態カード描画（PLCStatusCards）", opened)
            check("アラーム履歴カード描画（AlarmHistoryTable）",
                  wait_visible('text=アラーム履歴'))
            check("エラーログカード描画（ErrorLogTable）",
                  wait_visible('text=エラーログ'))

            # --- 設備詳細: インシデント追跡タブ ---
            print("\n[3] equipment detail -> incidents tab")
            check("インシデント一覧カード描画（IncidentTable）",
                  open_tab("インシデント追跡", '.v-card-title:has-text("インシデント追跡")'))

            # --- /errors-alarms 単体ページ ---
            print("\n[4] /errors-alarms standalone page")
            page.goto(f"{BASE}/errors-alarms", timeout=20000)
            try:
                # click は要素の出現を自動待機するので固定sleepは不要。
                page.click('div.v-select', timeout=5000)
                page.locator('.v-list-item').first.click(timeout=5000)
            except PlaywrightTimeout:
                print("    (設備選択をスキップ: セレクタ未検出)")
            check("errors-alarmsページでエラーログ描画",
                  wait_visible('text=エラーログ'))

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
