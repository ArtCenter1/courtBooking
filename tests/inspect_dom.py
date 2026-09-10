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
        
        res = await slot.evaluate("""
            el => {
                let curr = el;
                const path = [];
                while (curr && curr !== document.body) {
                    path.push({
                        tag: curr.tagName,
                        className: curr.className,
                        id: curr.id,
                        onclick: curr.getAttribute('onclick'),
                        href: curr.getAttribute('href')
                    });
                    curr = curr.parentElement;
                }
                return {
                    outerHTML: el.outerHTML,
                    parentHTML: el.parentElement ? el.parentElement.outerHTML : '',
                    ancestors: path
                };
            }
        """)
        import json
        print("DOM_INSPECT:", json.dumps(res, indent=2, ensure_ascii=False))
        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
