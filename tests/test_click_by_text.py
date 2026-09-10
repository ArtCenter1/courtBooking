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
        
        # Switch to Court B
        tab_links = page.locator('.r-tab__link')
        await tab_links.nth(1).click()
        await page.wait_for_timeout(800)
        
        # LOCATE BY TEXT 17~18 on Day 11!
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) .timeline__identity:has-text("17~18")').first
        print("Slot count:", await slot.count())
        print("Slot outerHTML:", await slot.evaluate('el => el.outerHTML'))
        print("Slot parent outerHTML:", await slot.evaluate('el => el.parentElement.outerHTML'))
        
        print("\n--- NOW CLICKING 17~18 ---")
        await slot.click()
        await page.wait_for_timeout(3000)
        
        print("Current URL:", page.url)
        print("Has 場地資訊:", await page.locator('text="場地資訊"').count() > 0)
        print("Has 預約 Reserve:", await page.locator('button:has-text("預約 Reserve")').count() > 0)
        
        # Take screenshot of reservation page
        await page.screenshot(path="tests/test_17_18_clicked.png")
        print("Saved tests/test_17_18_clicked.png")

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
