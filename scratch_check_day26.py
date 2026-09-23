import asyncio
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def check_day26():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state=r'C:\Users\artce\scripts\state.json')
        page = await ctx.new_page()
        await page.goto('https://gym.dga.sinica.edu.tw/reservation.html', wait_until='networkidle')
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        
        tab_links = page.locator('.r-tab__link')
        for court in ['A', 'B']:
            sec_id = '#js-v1' if court == 'A' else '#js-v2'
            if court == 'B':
                await tab_links.nth(1).click(force=True)
            else:
                await tab_links.first.click(force=True)
            await page.wait_for_timeout(600)
            
            day_item = page.locator(f'{sec_id} .calendar__day-item:has(.calendar__day-text:has-text("26"))')
            slots = await day_item.locator('.timeline__identity').all()
            print(f'=== Court {court} Day 26 Status ===')
            for s in slots:
                title = await s.get_attribute('title') or ''
                txt = (await s.inner_text()).strip()
                print(f'  {title:<25} | {txt}')
        await b.close()

if __name__ == '__main__':
    asyncio.run(check_day26())
