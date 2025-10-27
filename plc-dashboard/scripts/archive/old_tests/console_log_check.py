from playwright.sync_api import sync_playwright
import time
import sys

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    def handle_console(msg):
        try:
            text = msg.text
            # UTF-8でエンコードできる文字のみ保存
            console_logs.append(f'[{msg.type}] {text}')
        except:
            console_logs.append(f'[{msg.type}] <encoding error>')

    page.on('console', handle_console)

    # Login
    page.goto('http://localhost:3000/', wait_until='networkidle')
    page.fill('input[type="text"]', 'admin')
    page.fill('input[type="password"]', 'plc-monitor-2025')
    page.click('button:has-text("ログイン")')
    time.sleep(2)

    # Monitoring page
    page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle')
    time.sleep(20)

    # Check canvas
    canvas_count = page.locator('canvas').count()

    # Output results (ASCII only)
    print(f'Canvas count: {canvas_count}')
    print(f'\nTotal console logs: {len(console_logs)}')

    # Check for specific logs
    init_logs = [log for log in console_logs if 'init' in log.lower() or 'chart' in log.lower()]
    update_logs = [log for log in console_logs if 'update' in log.lower() or 'data' in log.lower()]

    print(f'\nChart initialization logs: {len(init_logs)}')
    for log in init_logs[:10]:
        try:
            # Remove emojis and non-ASCII
            clean_log = ''.join(char for char in log if ord(char) < 128)
            print(f'  {clean_log}')
        except:
            print('  <log encoding error>')

    print(f'\nChart update logs: {len(update_logs)}')
    for log in update_logs[:10]:
        try:
            clean_log = ''.join(char for char in log if ord(char) < 128)
            print(f'  {clean_log}')
        except:
            print('  <log encoding error>')

    page.screenshot(path='console_check.png', full_page=True)
    print(f'\nScreenshot: console_check.png')

    browser.close()
