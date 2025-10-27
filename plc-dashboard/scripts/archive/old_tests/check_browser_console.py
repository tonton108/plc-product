"""
ブラウザコンソールログを詳しく確認するスクリプト
"""
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwrightがインストールされていません")
    sys.exit(1)

def check_console_logs(equipment_id="LINE_A_001"):
    """コンソールログを収集"""
    print(f"=== コンソールログ確認: {equipment_id} ===\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_logs = []

        def handle_console(msg):
            console_logs.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            })

        page.on('console', handle_console)

        try:
            # ログイン
            print("1. ログイン中...")
            page.goto("http://localhost:3000/", wait_until='networkidle', timeout=30000)
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            page.wait_for_timeout(2000)

            # モニタリングページ
            url = f"http://localhost:3000/monitoring/{equipment_id}"
            print(f"2. モニタリングページにアクセス: {url}")
            page.goto(url, wait_until='networkidle', timeout=30000)

            # 20秒待機してデータ蓄積
            print("3. 20秒待機中...")
            page.wait_for_timeout(20000)

            # コンソールログを出力
            print("\n=== コンソールログ（全件） ===")
            for i, log in enumerate(console_logs, 1):
                print(f"{i}. [{log['type']}] {log['text']}")

            # グラフ状態を確認
            chart_status = page.evaluate("""
                () => {
                    const canvases = document.querySelectorAll('canvas');
                    return {
                        canvasCount: canvases.length
                    };
                }
            """)

            print(f"\n=== Canvas要素数: {chart_status['canvasCount']} ===")

            browser.close()

        except Exception as e:
            print(f"\nエラー: {e}")
            browser.close()

if __name__ == '__main__':
    check_console_logs()
