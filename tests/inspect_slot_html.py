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
            storage_state=r"d:\My_Projects\courtBooking\state.json",
            ignore_https_errors=True
        )
        page = await context.new_page()
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        has_logout = await page.locator("text=登出").count() > 0
        print("Has 登出 (logged in):", has_logout)
        
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        await page.locator('.r-tab__link').nth(1).click()
        await page.wait_for_timeout(1000)
        
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("12")) :text("14~15")').first
        if await slot.count() > 0:
            print("OuterHTML:", await slot.evaluate("e => e.outerHTML"))
            print("ParentHTML:", await slot.evaluate("e => e.parentElement.outerHTML"))
            print("GrandParentHTML:", await slot.evaluate("e => e.parentElement.parentElement.outerHTML"))
            print("Clickable?:", await slot.evaluate("e => e.onclick !== null || e.getAttribute('onclick') !== null"))
            print("Tag name:", await slot.evaluate("e => e.tagName"))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
