from playwright.sync_api import sync_playwright
import time
import json

with sync_playwright() as p:
    # Launch browser with no cache
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080}
    )
    page = context.new_page()

    # Collect all console logs
    console_logs = []
    page.on('console', lambda msg: console_logs.append({
        'type': msg.type,
        'text': msg.text
    }))

    # Login
    page.goto('http://localhost:3000/', wait_until='networkidle')
    page.fill('input[type="text"]', 'admin')
    page.fill('input[type="password"]', 'plc-monitor-2025')
    page.click('button:has-text("ログイン")')
    time.sleep(2)

    # Monitoring page with hard reload
    page.goto('http://localhost:3000/monitoring/LINE_A_001', wait_until='networkidle')
    page.reload(wait_until='networkidle')
    time.sleep(20)

    # Deep inspection of chart data
    result = page.evaluate('''
        () => {
            // Try multiple ways to access Vue data

            // Method 1: Check if useChartManagement is being used
            const scriptTags = Array.from(document.querySelectorAll('script'))
                .map(s => s.src)
                .filter(src => src.includes('useChartManagement'));

            // Method 2: Check for Chart component
            const chartComponents = document.querySelectorAll('[class*="chart"]');

            // Method 3: Check v-if condition elements
            const waitingDivs = document.querySelectorAll('.text-h6');
            const canvases = document.querySelectorAll('canvas');

            // Method 4: Try to find any reactive data
            const vueRoot = document.querySelector('#__nuxt');

            return {
                scripts: scriptTags,
                chartComponentsCount: chartComponents.length,
                waitingDivsCount: waitingDivs.length,
                canvasesCount: canvases.length,
                waitingTexts: Array.from(waitingDivs).map(d => d.textContent.trim()),
                hasVueRoot: !!vueRoot,
                timestamp: new Date().toISOString()
            };
        }
    ''')

    print('=== DEEP CHART DATA INSPECTION ===')
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print('\n=== CONSOLE LOGS (last 30) ===')
    for log in console_logs[-30:]:
        # Remove emojis to avoid encoding errors
        clean_text = log['text'].encode('ascii', 'ignore').decode('ascii')
        print(f"[{log['type']}] {clean_text}")

    # Take screenshot
    page.screenshot(path='deep_inspect_chart_data.png', full_page=True)
    print('\nScreenshot saved: deep_inspect_chart_data.png')

    browser.close()
