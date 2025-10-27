from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    # Launch browser with cache disabled
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        ignore_https_errors=True,
        java_script_enabled=True
    )

    # Disable cache
    page = context.new_page()
    page.route('**/*', lambda route: route.continue_())

    # Login
    page.goto('http://localhost:3000/', wait_until='networkidle')
    page.fill('input[type="text"]', 'admin')
    page.fill('input[type="password"]', 'plc-monitor-2025')
    page.click('button:has-text("ログイン")')
    time.sleep(2)

    # Monitoring page with hard reload
    page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle')
    page.reload(wait_until='networkidle')  # Hard reload
    time.sleep(20)

    # Check canvas
    canvas_count = page.locator('canvas').count()

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

    page.screenshot(path='no_cache_test.png', full_page=True)
    print(f'Screenshot: no_cache_test.png')

    browser.close()
