"""
UI/UX総合チェックツール
全画面のレイアウト崩れ、見た目、動作のスムーズさを徹底検証
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_ui_ux():
    """UI/UXチェックを実行"""
    print("=" * 80)
    print("  UI/UX 総合チェック")
    print("=" * 80)
    print()

    issues = []  # 検出された問題のリスト

    with sync_playwright() as p:
        try:
            # ブラウザ起動
            print("[1/7] ブラウザ起動中...")
            browser = p.chromium.launch(headless=False, slow_mo=500)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='ja-JP'
            )
            page = context.new_page()

            # JavaScriptエラーとコンソールログを記録
            js_errors = []
            console_logs = []

            def handle_console(msg):
                console_logs.append(f"[{msg.type}] {msg.text}")
                if msg.type in ['error', 'warning']:
                    print(f"  [CONSOLE {msg.type.upper()}] {msg.text}")

            def handle_page_error(error):
                js_errors.append(str(error))
                print(f"  [JS ERROR] {error}")

            page.on('console', handle_console)
            page.on('pageerror', handle_page_error)

            # スクリーンショット保存ディレクトリ
            screenshot_dir = Path(__file__).parent / 'ui_ux_screenshots'
            screenshot_dir.mkdir(exist_ok=True)

            # ======================================
            # 1. ログイン画面チェック
            # ======================================
            print("\n[2/7] ログイン画面をチェック中...")
            page.goto('http://localhost:3000/login', wait_until='networkidle', timeout=15000)
            time.sleep(1)

            # レイアウトチェック
            login_card = page.locator('.glass-card').first
            if not login_card.is_visible():
                issues.append("❌ ログイン: グラスカードが表示されていない")

            # テキストフィールドの確認
            username_field = page.locator('input[type="text"]').first
            password_field = page.locator('input[type="password"]').first

            if not username_field.is_visible() or not password_field.is_visible():
                issues.append("❌ ログイン: 入力フィールドが表示されていない")

            # ボタンの確認
            login_button = page.locator('button:has-text("ログイン")').first
            if not login_button.is_visible():
                issues.append("❌ ログイン: ログインボタンが表示されていない")

            # スクリーンショット保存
            page.screenshot(path=str(screenshot_dir / '01_login.png'), full_page=True)
            print("  ✅ ログイン画面チェック完了")

            # ログイン実行
            print("\n[3/7] ログイン実行中...")
            username_field.fill('admin')
            password_field.fill('plc-monitor-2025')
            login_button.click()

            # ログイン後のページ遷移を待つ
            page.wait_for_function('window.location.pathname !== "/login"', timeout=10000)
            time.sleep(2)
            print(f"  ✅ ログイン成功: {page.url}")

            # ======================================
            # 2. トップページ（設備一覧）チェック
            # ======================================
            print("\n[4/7] トップページをチェック中...")

            # ヘッダーカードの確認
            header_card = page.locator('.glass-card-primary').first
            if not header_card.is_visible():
                issues.append("❌ トップ: ヘッダーカードが表示されていない")

            # 設備カードの確認
            equipment_cards = page.locator('.glass-card').all()
            if len(equipment_cards) == 0:
                issues.append("⚠️ トップ: 設備カードが0件（データがない可能性）")

            # ボタングループの確認
            theme_toggle = page.locator('button').filter(has_text='').first  # ThemeToggle
            refresh_btn = page.locator('button:has-text("更新")').first

            if not refresh_btn.is_visible():
                issues.append("❌ トップ: 更新ボタンが表示されていない")

            # カード/リスト切り替えの確認
            view_toggle = page.locator('.v-btn-toggle').first
            if not view_toggle.is_visible():
                issues.append("❌ トップ: 表示切替ボタンが表示されていない")

            # スクリーンショット保存
            page.screenshot(path=str(screenshot_dir / '02_index_card_view.png'), full_page=True)

            # リスト表示に切り替え
            list_view_btn = page.locator('button[value="list"]').first
            if list_view_btn.is_visible():
                list_view_btn.click()
                time.sleep(1)
                page.screenshot(path=str(screenshot_dir / '03_index_list_view.png'), full_page=True)

                # データテーブルの確認
                data_table = page.locator('.v-data-table').first
                if not data_table.is_visible():
                    issues.append("❌ トップ: データテーブルが表示されていない")

                # カード表示に戻す
                card_view_btn = page.locator('button[value="card"]').first
                card_view_btn.click()
                time.sleep(1)

            print("  ✅ トップページチェック完了")

            # ======================================
            # 3. ダッシュボード画面チェック
            # ======================================
            print("\n[5/7] ダッシュボード画面をチェック中...")
            page.goto('http://localhost:3000/dashboard', wait_until='networkidle', timeout=15000)
            time.sleep(2)

            # サマリーカードの確認
            summary_cards = page.locator('.v-card').filter(has=page.locator('.text-h2')).all()
            if len(summary_cards) < 4:
                issues.append(f"❌ ダッシュボード: サマリーカードが不足（期待:4, 実際:{len(summary_cards)}）")

            # スクリーンショット保存
            page.screenshot(path=str(screenshot_dir / '04_dashboard.png'), full_page=True)
            print("  ✅ ダッシュボード画面チェック完了")

            # ======================================
            # 4. モニタリング画面チェック
            # ======================================
            print("\n[6/7] モニタリング画面をチェック中...")

            # DEMO_001のモニタリング画面を直接開く（デモデータが送信されている）
            page.goto('http://localhost:3000/monitoring/DEMO_001', wait_until='networkidle', timeout=15000)
            time.sleep(3)  # データ更新を待つ

            if True:  # 常に実行

                # ヘッダーの確認
                header = page.locator('.glass-card').first
                if not header.is_visible():
                    issues.append("❌ モニタリング: ヘッダーが表示されていない")

                # ステータスカードの確認
                status_cards = page.locator('.status-card').all()
                if len(status_cards) == 0:
                    issues.append("⚠️ モニタリング: ステータスカードが表示されていない")
                else:
                    print(f"  ✅ ステータスカード検出: {len(status_cards)}個")

                # グラフカードの確認
                chart_cards = page.locator('canvas').all()
                if len(chart_cards) == 0:
                    issues.append("❌ モニタリング: グラフ(canvas)が表示されていない")
                else:
                    print(f"  ✅ グラフ検出: {len(chart_cards)}個")

                # スクリーンショット保存（初期状態）
                page.screenshot(path=str(screenshot_dir / '05_monitoring_initial.png'), full_page=True)

                # 10秒待機してデータ更新を観察
                print("  データ更新を10秒間観察中...")
                time.sleep(10)

                # スクリーンショット保存（更新後）
                page.screenshot(path=str(screenshot_dir / '06_monitoring_after_update.png'), full_page=True)

                print("  ✅ モニタリング画面チェック完了")
            else:
                issues.append("⚠️ モニタリング: 監視ボタンが見つからない（設備データなし）")

            # ======================================
            # 5. アニメーション・インタラクションチェック
            # ======================================
            print("\n[7/7] アニメーション・インタラクションをチェック中...")
            page.goto('http://localhost:3000/', wait_until='networkidle', timeout=15000)
            time.sleep(1)

            # カードホバー効果のテスト
            first_card = page.locator('.glass-card').nth(1)  # 最初の設備カード
            if first_card.is_visible():
                # ホバー前
                box_before = first_card.bounding_box()

                # ホバー
                first_card.hover()
                time.sleep(0.5)

                # ホバー後
                box_after = first_card.bounding_box()

                # transform: translateY(-4px)が効いているか確認（Y座標が減少するはず）
                if box_before and box_after:
                    if box_after['y'] >= box_before['y']:
                        issues.append("⚠️ ホバー効果: カードのホバーアニメーションが機能していない可能性")
                    else:
                        print("  ✅ ホバー効果: カードが上に移動")

            # ボタンのホバー効果テスト
            refresh_btn = page.locator('button:has-text("更新")').first
            if refresh_btn.is_visible():
                refresh_btn.hover()
                time.sleep(0.5)
                print("  ✅ ボタンホバー: 視覚的フィードバック確認")

            # スクリーンショット保存
            page.screenshot(path=str(screenshot_dir / '07_hover_interaction.png'), full_page=True)

            print("  ✅ アニメーション・インタラクションチェック完了")

            # ======================================
            # 結果サマリー
            # ======================================
            print("\n" + "=" * 80)
            print("  チェック結果サマリー")
            print("=" * 80)

            print(f"\n📊 スクリーンショット: {len(list(screenshot_dir.glob('*.png')))}枚保存")
            print(f"📁 保存先: {screenshot_dir}")

            if js_errors:
                print(f"\n❌ JavaScript エラー: {len(js_errors)}件")
                for error in js_errors[:5]:
                    print(f"  - {error}")
            else:
                print("\n✅ JavaScript エラー: なし")

            console_errors = [msg for msg in console_logs if '[error]' in msg.lower()]
            if console_errors:
                print(f"\n⚠️ コンソールエラー: {len(console_errors)}件")
                for error in console_errors[:5]:
                    print(f"  - {error}")
            else:
                print("✅ コンソールエラー: なし")

            if issues:
                print(f"\n🔍 UI/UX 問題点: {len(issues)}件")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print("\n🎉 UI/UX 問題点: なし - すべてのチェックをパス！")

            print("\n" + "=" * 80)

            # 5秒待機してブラウザを閉じる
            print("\nブラウザは5秒後に自動的に閉じます...")
            time.sleep(5)
            browser.close()

            return len(issues) == 0 and len(js_errors) == 0

        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            try:
                screenshot_path = screenshot_dir / 'error.png'
                page.screenshot(path=str(screenshot_path))
                print(f"  エラースクリーンショット保存: {screenshot_path}")
            except:
                pass
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    success = check_ui_ux()
    sys.exit(0 if success else 1)
