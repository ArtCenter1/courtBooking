import asyncio
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

async def inspect():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state=r"C:\Users\artce\scripts\state.json", ignore_https_errors=True)
        page = await ctx.new_page()
        
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        print("Logged in text:", [l.strip() for l in (await page.inner_text('body')).split('\n') if '郭' in l or '登' in l])
        
        # Select Tennis court
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(500)
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(500)
        
        # Check what tabs exist
        tab_links = page.locator('.r-tab__link')
        print("Tab count:", await tab_links.count())
        for i in range(await tab_links.count()):
            print(f"Tab {i} text:", await tab_links.nth(i).inner_text())
            
        # Switch to Court B
        await tab_links.nth(1).click()
        await page.wait_for_timeout(1000)
        
        # What dates are displayed in #js-v2?
        dates = await page.locator('#js-v2 .calendar__day-text').all_inner_texts()
        print("Dates in #js-v2:", [d.strip() for d in dates])
        
        # Check if 11 is in dates
        day11_items = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11"))')
        print("Day 11 count in #js-v2:", await day11_items.count())
        
        if await day11_items.count() > 0:
            titles = await day11_items.first.locator('.timeline__identity').evaluate_all('els => els.map(e => ({title: e.getAttribute("title"), text: e.innerText.trim()}))')
            print("Day 11 slots count:", len(titles))
            for t in titles:
                print("  ", t)

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
