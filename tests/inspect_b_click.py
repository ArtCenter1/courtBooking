import asyncio
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

async def inspect_b():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state=r"C:\Users\artce\scripts\state.json")
        page = await ctx.new_page()
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(500)

        # Switch to Court B
        tab_links = page.locator('.r-tab__link')
        print("Tab count:", await tab_links.count())
        await tab_links.nth(1).click(force=True)
        await page.wait_for_timeout(800)
        
        # Inspect element 17:00~18:00 on day 11
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) .timeline__identity[title^="17:00~"]').first
        print("Slot count:", await slot.count())
        if await slot.count() > 0:
            print("Target text:", await slot.inner_text())
            print("Target title:", await slot.get_attribute("title"))
            print("Clicking target slot...")
            await slot.click()
            await page.wait_for_timeout(3000)
            print("URL after click:", page.url)
            print("Reservation header visible:", await page.locator('text="場地資訊"').count() > 0)
            print("Reserve button visible:", await page.locator('button:has-text("預約 Reserve"), button:has-text("預約")').count() > 0)
            await page.screenshot(path="real_17_click.png")
            print("Saved real_17_click.png")

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect_b())
