from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_logs = []
    def handle_console(msg):
        try:
            console_logs.append(f'[{msg.type}] {msg.text}')
        except:
            pass

    page.on('console', handle_console)

    # Login
    page.goto('http://localhost:3000/', wait_until='networkidle')
    page.fill('input[type="text"]', 'admin')
    page.fill('input[type="password"]', 'plc-monitor-2025')
    page.click('button:has-text("ログイン")')
    time.sleep(2)

    # Monitoring page
    page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle')
    print('Page loaded, waiting 20 seconds...')
    time.sleep(20)

    # Check canvas elements
    canvas_count = page.locator('canvas').count()
    print(f'\n=== RESULT ===')
    print(f'Canvas elements: {canvas_count}')

    # Check chart update logs
    update_logs = [log for log in console_logs if 'chart update' in log.lower() or 'update success' in log.lower()]
    print(f'Chart update logs: {len(update_logs)}')
    if update_logs:
        print('Latest update logs (last 5):')
        for log in update_logs[-5:]:
            print(f'  {log}')

    # Screenshot
    page.screenshot(path='scripts/final_test.png', full_page=True)
    print(f'\nScreenshot: scripts/final_test.png')

    browser.close()
