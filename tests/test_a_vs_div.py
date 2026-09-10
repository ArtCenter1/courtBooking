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
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=r"C:\Users\artce\scripts\state.json",
            ignore_https_errors=True
        )
        page = await context.new_page()
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(500)
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(500)
        
        # Switch to Court B
        await page.locator('.r-tab__link').nth(1).click()
        await page.wait_for_timeout(800)
        
        # Target explicitly the <a> tag
        link = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) a:has-text("17~18")').first
        print("Link count:", await link.count())
        print("Link tag:", await link.evaluate("e => e.tagName"))
        print("Link id:", await link.evaluate("e => e.id"))
        print("Link onclick:", await link.evaluate("e => e.getAttribute('onclick')"))
        
        print("Clicking the <a> tag directly...")
        await link.click()
        await page.wait_for_timeout(3000)
        
        print("URL after clicking <a>:", page.url)
        print("Has 場地資訊:", await page.locator(':has-text("場地資訊")').count() > 0)
        print("Has 預約 Reserve:", await page.locator('button:has-text("預約 Reserve")').count() > 0)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
