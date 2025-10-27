from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # ブラウザを表示
    page = browser.new_page()

    console_logs = []
    def handle_console(msg):
        log_entry = f'[{msg.type}] {msg.text}'
        console_logs.append(log_entry)
        print(f'  {log_entry}')

    page.on('console', handle_console)

    # Login
    print('1. ログイン中...')
    page.goto('http://localhost:3000/', wait_until='networkidle')
    page.fill('input[type="text"]', 'admin')
    page.fill('input[type="password"]', 'plc-monitor-2025')
    page.click('button:has-text("ログイン")')
    time.sleep(2)

    # Monitoring page
    print('2. モニタリングページにアクセス...')
    page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle')

    print('3. 20秒待機中...')
    time.sleep(20)

    # Check canvas elements
    canvas_count = page.locator('canvas').count()
    print(f'\n=== 結果 ===')
    print(f'Canvas要素数: {canvas_count}')

    # Check chart configs via JS
    chart_info = page.evaluate('''
        () => {
            const chartCards = document.querySelectorAll('.chart-container');
            const canvases = document.querySelectorAll('canvas');
            const waitingMessages = document.querySelectorAll('.chart-container .text-h6');

            return {
                chartCards: chartCards.length,
                canvases: canvases.length,
                waitingMessages: waitingMessages.length
            };
        }
    ''')

    print(f'Chart cards: {chart_info["chartCards"]}')
    print(f'Canvases: {chart_info["canvases"]}')
    print(f'Waiting messages: {chart_info["waitingMessages"]}')

    # Screenshot
    page.screenshot(path='scripts/detailed_check.png', full_page=True)
    print(f'\nスクリーンショット: scripts/detailed_check.png')

    print('\nブラウザを60秒間開いたままにします（手動確認用）...')
    time.sleep(60)

    browser.close()
