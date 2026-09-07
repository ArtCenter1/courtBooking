import asyncio
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1400, 'height': 950})
        page.on('dialog', lambda dialog: dialog.accept())
        page.on('console', lambda msg: print('BROWSER CONSOLE:', msg.text))
        
        # Pre-set token in localStorage
        token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0IiwiZW1haWwiOiJ1c2VyMUB0ZXN0LmNvbSIsImV4cCI6MTc4OTM4OTM5NH0.1PAbxY4LGyLIQCVyV9oaGcpoyCRfNl18VHHoNMo32Y4'
        await page.add_init_script(f"localStorage.setItem('court_jwt_token', '{token}');")
        
        await page.goto('http://127.0.0.1:8000/')
        print('Page loaded with token.')
        await page.wait_for_timeout(1000)
        
        # Click scan button
        scan_btn = page.locator('#full-radar-scan-btn')
        print('Clicking scan button...')
        await scan_btn.click()
        
        # Wait for calendar matrix to appear
        print('Waiting for #matrix-section-card...')
        await page.wait_for_selector('#matrix-section-card', state='visible', timeout=60000)
        print('Matrix card visible!')
        
        # Take screenshot of Court A
        await page.screenshot(path=r'C:\Users\artce\.gemini\antigravity-ide\brain\4cdb4fb8-ff76-4955-ae56-7d53cfdba8aa\sinica_recreation_court_a.png', full_page=True)
        print('Court A screenshot saved!')
        
        # Click Court B
        await page.locator('#court-tab-b').click()
        await page.wait_for_timeout(500)
        await page.screenshot(path=r'C:\Users\artce\.gemini\antigravity-ide\brain\4cdb4fb8-ff76-4955-ae56-7d53cfdba8aa\sinica_recreation_court_b.png')
        print('Court B screenshot saved!')
        
        # Click an open slot to test priority picking
        available_slots = page.locator('.timeline__identity.slot-available')
        count = await available_slots.count()
        print(f'Available slots found on Court B: {count}')
        if count > 0:
            await available_slots.first.click()
            await page.wait_for_timeout(400)
            if count > 1:
                await available_slots.nth(1).click()
                await page.wait_for_timeout(400)
        
        await page.screenshot(path=r'C:\Users\artce\.gemini\antigravity-ide\brain\4cdb4fb8-ff76-4955-ae56-7d53cfdba8aa\sinica_recreation_picked.png', full_page=True)
        print('Selection test screenshot saved!')
        await browser.close()

if __name__ == '__main__':
    asyncio.run(verify())
