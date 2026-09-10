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
        ctx = await b.new_context(storage_state=r"C:\Users\artce\scripts\state.json")
        page = await ctx.new_page()
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(500)
        
        tab_links = page.locator('.r-tab__link')
        await tab_links.nth(1).click(force=True)
        await page.wait_for_timeout(800)
        
        slot = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("11")) .timeline__identity[title^="17:00~"]').first
        
        # Check jQuery events
        events_info = await slot.evaluate("""
            el => {
                const info = {};
                if (window.$ || window.jQuery) {
                    const $ = window.$ || window.jQuery;
                    const elEvents = $._data(el, 'events');
                    const parentEvents = $._data(el.parentElement, 'events');
                    const docEvents = $._data(document, 'events');
                    return {
                        hasJquery: true,
                        elEvents: elEvents ? Object.keys(elEvents) : null,
                        parentEvents: parentEvents ? Object.keys(parentEvents) : null,
                        docEvents: docEvents ? Object.keys(docEvents) : null
                    };
                }
                return { hasJquery: false };
            }
        """)
        print("EVENTS INFO:", events_info)
        
        # Let's see what happens if we click with mouse.click at element center
        box = await slot.bounding_box()
        print("Bounding box:", box)
        if box:
            print("Clicking at center of bounding box with mouse...")
            await page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            await page.wait_for_timeout(3000)
            print("After mouse click, URL:", page.url)
            print("Has 場地資訊:", await page.locator('text="場地資訊"').count())
            print("Has 預約 Reserve:", await page.locator('button:has-text("預約 Reserve")').count())
            await page.screenshot(path="tests/after_mouse_click.png")

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
