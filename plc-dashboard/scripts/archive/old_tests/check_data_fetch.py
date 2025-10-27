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

    # Check if data is displayed
    result = page.evaluate('''
        () => {
            // Check status cards
            const statusCards = document.querySelectorAll('.status-card');
            const statusValues = Array.from(statusCards).map(card => {
                const valueEl = card.querySelector('.text-h3');
                return valueEl ? valueEl.textContent.trim() : 'N/A';
            });

            // Check data table
            const tableRows = document.querySelectorAll('tbody tr');
            const tableData = Array.from(tableRows).slice(0, 3).map(row => {
                const cells = row.querySelectorAll('td');
                return Array.from(cells).map(cell => cell.textContent.trim());
            });

            return {
                statusCardCount: statusCards.length,
                statusValues: statusValues,
                tableRowCount: tableRows.length,
                tableData: tableData
            };
        }
    ''')

    print('=== DATA CHECK ===')
    print(f'Status cards: {result["statusCardCount"]}')
    print(f'Status values: {result["statusValues"]}')
    print(f'Table rows: {result["tableRowCount"]}')
    print(f'Table data (first 3 rows):')
    for i, row in enumerate(result["tableData"], 1):
        print(f'  Row {i}: {row}')

    # Check if data has actual values (not N/A)
    has_data = any(val != 'N/A' and val != '' for val in result["statusValues"])
    print(f'\nData is being fetched: {has_data}')

    browser.close()
