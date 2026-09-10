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
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized'
            ]
        )
        context = await browser.new_context(
            storage_state=r"C:\Users\artce\scripts\state.json",
            ignore_https_errors=True,
            no_viewport=True,
            locale='zh-TW'
        )
        # Stealth init script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
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
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) a.timeline__rez-link:has-text("17~18"), #js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) .timeline__identity:has-text("17~18")').first
        await slot.click()
        await page.wait_for_timeout(2500)
        
        # reCAPTCHA anchor
        recaptcha_frame = page.frame_locator('iframe[title*="reCAPTCHA"], iframe[src*="recaptcha"]').first
        anchor = recaptcha_frame.locator('#recaptcha-anchor, .recaptcha-checkbox')
        print("Clicking reCAPTCHA anchor with human delay...")
        await page.wait_for_timeout(600)
        await anchor.click()
        await page.wait_for_timeout(2500)
        
        # Check aria-checked
        checked_el = recaptcha_frame.locator('#recaptcha-anchor[aria-checked="true"]')
        has_checked = await checked_el.count() > 0
        print("IS RECAPTCHA CHECKED (GREEN TICK):", has_checked)
        
        await page.screenshot(path="tests/stealth_result.png")
        print("Saved tests/stealth_result.png")
        
        # Safely click back
        back_btn = page.locator('button:has-text("返回 Back"), a:has-text("返回 Back"), text="返回 Back"')
        if await back_btn.count() > 0:
            await back_btn.first.click()
            await page.wait_for_timeout(1000)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
