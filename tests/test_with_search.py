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
        b = await p.chromium.launch(headless=False)
        ctx = await b.new_context(storage_state=r"C:\Users\artce\scripts\state.json")
        page = await ctx.new_page()
        page.on("request", lambda req: print(f"[REQ] {req.method} {req.url} {req.post_data[:100] if req.post_data else ''}"))
        
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(500)
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(500)
        
        # CLICK SEARCH!
        print("CLICKING SEARCH BUTTON...")
        await page.locator('button:has-text("搜尋 Search")').click()
        await page.wait_for_timeout(1500)
        
        tab_links = page.locator('.r-tab__link')
        print("Clicking Court B tab...")
        await tab_links.nth(1).click()
        await page.wait_for_timeout(800)
        
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) .timeline__identity[title^="17:00~"]').first
        print("Slot exists:", await slot.count())
        print("Clicking slot 17:00~18:00...")
        await slot.click()
        await page.wait_for_timeout(3000)
        
        print("URL after click:", page.url)
        print("Has reservation header:", await page.locator('text="場地資訊"').count() > 0)
        print("Has reserve button:", await page.locator('button:has-text("預約 Reserve")').count() > 0)
        await page.screenshot(path="tests/after_search_click.png")

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
