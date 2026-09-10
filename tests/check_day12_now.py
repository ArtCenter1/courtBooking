import asyncio
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=r"d:\My_Projects\courtBooking\state.json",
            ignore_https_errors=True
        )
        page = await context.new_page()
        await page.goto('https://gym.dga.sinica.edu.tw/reservation.html', wait_until='networkidle')
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        
        # Court A, Day 12
        items_a = await page.locator('#js-v1 .calendar__day-item:has(.calendar__day-text:has-text("12")) :is(.timeline__identity, a.timeline__rez-link)').all()
        print(f"=== Court A Day 12 ({len(items_a)} items) ===")
        for el in items_a:
            tag = await el.evaluate("e => e.tagName")
            txt = (await el.inner_text()).replace('\n', ' ')
            title = await el.get_attribute("title") or ""
            print(f"  [{tag}] {title} | {txt}")
            
        # Switch to Court B
        await page.locator('.r-tab__link').nth(1).click()
        await page.wait_for_timeout(1000)
        items_b = await page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("12")) :is(.timeline__identity, a.timeline__rez-link)').all()
        print(f"=== Court B Day 12 ({len(items_b)} items) ===")
        for el in items_b:
            tag = await el.evaluate("e => e.tagName")
            txt = (await el.inner_text()).replace('\n', ' ')
            title = await el.get_attribute("title") or ""
            print(f"  [{tag}] {title} | {txt}")
            
        # Take a screenshot of the calendar
        await page.screenshot(path="day12_status.png")
        print("Screenshot saved to day12_status.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
