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
        
        # Click search
        await page.locator('button:has-text("搜尋 Search")').click()
        await page.wait_for_timeout(1000)
        
        # Switch to Court B tab
        tab_links = page.locator('.r-tab__link')
        print("Switching to Court B...")
        await tab_links.nth(1).click()
        await page.wait_for_timeout(1000)
        
        # Find 17:00 on Day 11
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) .timeline__identity[title^="17:00~"]').first
        print("Slot count:", await slot.count())
        print("Slot text:", await slot.inner_text())
        print("Slot title:", await slot.get_attribute("title"))
        print("Slot class:", await slot.get_attribute("class"))
        
        # Try clicking slot
        print("\n--- ATTEMPTING CLICK ---")
        await slot.click()
        await page.wait_for_timeout(3000)
        
        print("Current URL:", page.url)
        print("Has reservation header:", await page.locator('text="場地資訊"').count() > 0)
        print("Has reserve button:", await page.locator('button:has-text("預約 Reserve")').count() > 0)
        
        await page.screenshot(path="tests/logged_in_click_result.png")
        print("Saved tests/logged_in_click_result.png")
        
        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
