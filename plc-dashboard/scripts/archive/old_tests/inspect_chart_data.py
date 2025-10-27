from playwright.sync_api import sync_playwright
import time
import json

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

    # Inspect chart data via JavaScript
    chart_data = page.evaluate('''
        () => {
            // Try to access Vue app instance
            try {
                const app = document.querySelector('#__nuxt');

                // Try different approaches to get chart data
                const charts = window.__NUXT__ || {};

                return {
                    hasNuxt: !!app,
                    nuxtData: Object.keys(charts).slice(0, 5),
                    message: 'Vue devtools inspection needed'
                };
            } catch (e) {
                return {
                    error: e.toString()
                };
            }
        }
    ''')

    print(json.dumps(chart_data, indent=2))

    browser.close()
