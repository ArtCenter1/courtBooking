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
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(500)
        
        # Check tab links
        tab_links = page.locator('.r-tab__link')
        print("Clicking tab 1 (Court B)...")
        await tab_links.nth(1).click()
        await page.wait_for_timeout(1000)
        
        # Check if #js-v2 is visible and active
        v1_display = await page.locator('#js-v1').evaluate('el => window.getComputedStyle(el).display')
        v2_display = await page.locator('#js-v2').evaluate('el => window.getComputedStyle(el).display')
        print("v1 display:", v1_display)
        print("v2 display:", v2_display)
        
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) .timeline__identity[title^="17:00~"]').first
        print("Slot visible:", await slot.is_visible())
        
        # Now let's find ALL click event listeners in window using getEventListeners if in Chrome, or walking all elements
        listeners = await page.evaluate("""() => {
            const allElements = document.querySelectorAll('*');
            const clicked = [];
            for (let el of allElements) {
                if (el.onclick) {
                    clicked.push({tag: el.tagName, id: el.id, class: el.className, onclick: el.onclick.toString().slice(0, 100)});
                }
            }
            return clicked;
        }""")
        print("ELEMENTS WITH ONCLICK:", len(listeners))
        for l in listeners:
            print("ONCLICK:", l)

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
