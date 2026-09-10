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
        
        # Click 17~18
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) .timeline__identity:has-text("17~18")').first
        await slot.click()
        await page.wait_for_timeout(2500)
        
        # Check reCAPTCHA frame
        recaptcha_frame = page.frame_locator('iframe[title*="reCAPTCHA"], iframe[src*="recaptcha"]').first
        anchor = recaptcha_frame.locator('#recaptcha-anchor, .recaptcha-checkbox')
        print("Anchor visible:", await anchor.is_visible())
        
        print("Clicking reCAPTCHA anchor...")
        await anchor.click()
        await page.wait_for_timeout(2000)
        
        # Check aria-checked
        is_checked = await recaptcha_frame.locator('#recaptcha-anchor[aria-checked="true"]').count() > 0
        print("reCAPTCHA checked (green tick):", is_checked)
        
        await page.screenshot(path="tests/recaptcha_checked.png")
        print("Saved tests/recaptcha_checked.png")
        
        # Click 返回 Back
        back_btn = page.locator('a:has-text("返回"), button:has-text("返回"), text="返回 Back"')
        if await back_btn.count() > 0:
            print("Clicking 返回 Back safely...")
            await back_btn.first.click()
            await page.wait_for_timeout(1500)
            print("Back on calendar:", "網球場" in (await page.inner_text('body')))

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
