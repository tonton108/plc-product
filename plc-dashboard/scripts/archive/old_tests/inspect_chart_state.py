from playwright.sync_api import sync_playwright
import time
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Enable console logging
    console_messages = []
    page.on('console', lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

    # Login
    page.goto('http://localhost:3000/', wait_until='networkidle')
    page.fill('input[type="text"]', 'admin')
    page.fill('input[type="password"]', 'plc-monitor-2025')
    page.click('button:has-text("ログイン")')
    time.sleep(2)

    # Monitoring page
    page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle')
    time.sleep(15)

    # Inspect Vue component state
    result = page.evaluate('''
        () => {
            // Try to access Vue app instance
            const app = document.querySelector('#__nuxt');

            // Check chart containers
            const chartContainers = document.querySelectorAll('.chart-container');
            const canvases = document.querySelectorAll('canvas');
            const waitingMessages = document.querySelectorAll('.chart-container .text-h6');

            // Check v-if elements
            const vIfElements = [];
            chartContainers.forEach((container, index) => {
                const hasCanvas = container.querySelector('canvas') !== null;
                const hasWaiting = container.querySelector('.text-h6') !== null;
                const waitingText = hasWaiting ? container.querySelector('.text-h6').textContent : null;

                vIfElements.push({
                    index: index,
                    hasCanvas: hasCanvas,
                    hasWaiting: hasWaiting,
                    waitingText: waitingText
                });
            });

            return {
                chartContainers: chartContainers.length,
                canvases: canvases.length,
                waitingMessages: waitingMessages.length,
                vIfElements: vIfElements
            };
        }
    ''')

    print('=== CHART STATE INSPECTION ===')
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print('\n=== CONSOLE MESSAGES ===')
    for msg in console_messages:
        print(msg)

    # Take screenshot
    page.screenshot(path='inspect_chart_state.png', full_page=True)
    print('\nScreenshot saved: inspect_chart_state.png')

    browser.close()
