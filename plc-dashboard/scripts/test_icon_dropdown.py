#!/usr/bin/env python3
"""
アイコン選択プルダウンの表示確認テスト
"""
import sys
import io
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_icon_dropdown():
    """アイコンプルダウンの表示をテスト"""
    with sync_playwright() as p:
        # CI環境ではheadlessモードで実行
        is_ci = os.environ.get('CI', 'false').lower() == 'true'
        headless_mode = is_ci

        print(f"🌐 ブラウザを起動中 (headless={headless_mode})...")
        browser = p.chromium.launch(headless=headless_mode)
        page = browser.new_page()

        # スクリーンショットディレクトリを作成
        screenshot_dir = Path("scripts/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Raspberry Pi Agent UIにアクセス
            print("📡 http://localhost:5001 にアクセス中...")
            page.goto("http://localhost:5001")
            time.sleep(2)

            # ログインページの確認
            page.screenshot(path="scripts/screenshots/raspi_login.png")
            print("✅ ログイン画面のスクリーンショット保存完了")

            # ログイン（デフォルト認証情報）
            print("🔐 ログイン中...")
            page.fill('input[name="username"]', 'admin')
            page.fill('input[name="password"]', 'admin')
            page.click('button[type="submit"]')
            time.sleep(2)

            # モニタリング画面に到達
            print("📊 モニタリング画面を確認中...")
            page.screenshot(path="scripts/screenshots/raspi_monitoring.png")
            print("✅ モニタリング画面のスクリーンショット保存完了")

            # 設定ボタンをクリック
            print("⚙️ 設定モーダルを開いています...")
            page.click('button:has-text("設定")')
            time.sleep(1)

            # 設定モーダルのスクリーンショット
            page.screenshot(path="scripts/screenshots/raspi_config_modal.png")
            print("✅ 設定モーダルのスクリーンショット保存完了")

            # PLCデータ項目を追加ボタンをクリック
            print("➕ PLCデータ項目を追加...")
            page.click('button:has-text("PLCデータ項目を追加")')
            time.sleep(1)

            # アイコンプルダウンの表示確認
            page.screenshot(path="scripts/screenshots/raspi_plc_item_form.png")
            print("✅ PLCデータ項目フォームのスクリーンショット保存完了")

            # アイコンプルダウンをクリックして展開
            print("🎨 アイコンプルダウンを展開中...")
            icon_selects = page.locator('select.icon-select')
            if icon_selects.count() > 0:
                icon_select = icon_selects.last()
                icon_select.click()
                time.sleep(0.5)

                # プルダウン展開時のスクリーンショット
                page.screenshot(path="scripts/screenshots/raspi_icon_dropdown_open.png")
                print("✅ アイコンプルダウン展開時のスクリーンショット保存完了")

                # プルダウンをフォーカス状態でスクリーンショット
                icon_select.focus()
                time.sleep(0.3)
                page.screenshot(path="scripts/screenshots/raspi_icon_dropdown_focused.png")
                print("✅ アイコンプルダウンフォーカス時のスクリーンショット保存完了")

            else:
                print("⚠️ アイコンプルダウンが見つかりませんでした")

            print("\n" + "="*60)
            print("📸 スクリーンショット保存先:")
            print("  - scripts/screenshots/raspi_login.png")
            print("  - scripts/screenshots/raspi_monitoring.png")
            print("  - scripts/screenshots/raspi_config_modal.png")
            print("  - scripts/screenshots/raspi_plc_item_form.png")
            print("  - scripts/screenshots/raspi_icon_dropdown_open.png")
            print("  - scripts/screenshots/raspi_icon_dropdown_focused.png")
            print("="*60)

            # 5秒待機（目視確認用）
            print("\n⏳ 5秒待機（目視確認用）...")
            time.sleep(5)

            print("\n✅ テスト完了！")

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            page.screenshot(path="scripts/screenshots/raspi_error.png")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    test_icon_dropdown()
