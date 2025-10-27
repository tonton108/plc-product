from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Login
    page.goto('http://localhost:3000/', wait_until='networkidle')
    page.fill('input[type="text"]', 'admin')
    page.fill('input[type="password"]', 'plc-monitor-2025')
    page.click('button:has-text("ログイン")')
    time.sleep(2)

    # Monitoring page
    page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle')
    time.sleep(20)

    # Check canvas elements
    canvas_count = page.locator('canvas').count()

    # Check chart info via JS
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

    print(f'Canvas count: {canvas_count}')
    print(f'Chart cards: {chart_info["chartCards"]}')
    print(f'Waiting messages: {chart_info["waitingMessages"]}')

    # Screenshot
    page.screenshot(path='simple_check.png', full_page=True)
    print(f'Screenshot: simple_check.png')

    browser.close()
