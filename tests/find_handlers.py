import asyncio
import sys
import json
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
        
        info = await page.evaluate("""() => {
            const res = {};
            const docEvts = window.$._data(document, 'events');
            if (docEvts) {
                res.doc = {};
                for (let k in docEvts) {
                    res.doc[k] = docEvts[k].map(h => ({
                        selector: h.selector,
                        code: h.handler ? h.handler.toString().slice(0, 400) : ''
                    }));
                }
            }
            const bodyEvts = window.$._data(document.body, 'events');
            if (bodyEvts) {
                res.body = {};
                for (let k in bodyEvts) {
                    res.body[k] = bodyEvts[k].map(h => ({
                        selector: h.selector,
                        code: h.handler ? h.handler.toString().slice(0, 400) : ''
                    }));
                }
            }
            return res;
        }""")
        print("HANDLERS:", json.dumps(info, indent=2, ensure_ascii=False))
        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
