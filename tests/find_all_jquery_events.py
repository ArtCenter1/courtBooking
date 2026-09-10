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
        
        tab_links = page.locator('.r-tab__link')
        await tab_links.nth(1).click()
        await page.wait_for_timeout(1000)
        
        events_found = await page.evaluate("""() => {
            const results = [];
            const all = document.querySelectorAll('*');
            for (let el of all) {
                const evts = window.$._data(el, 'events');
                if (evts) {
                    const keys = Object.keys(evts);
                    results.push({
                        tag: el.tagName,
                        id: el.id,
                        class: el.className,
                        events: keys,
                        details: keys.map(k => ({
                            event: k,
                            handlers: evts[k].map(h => ({
                                selector: h.selector,
                                code: h.handler ? h.handler.toString().slice(0, 100) : ''
                            }))
                        }))
                    });
                }
            }
            return results;
        }""")
        print(f"FOUND {len(events_found)} ELEMENTS WITH JQUERY EVENTS:")
        for ef in events_found:
            print(f"[{ef['tag']} id='{ef['id']}' class='{ef['class']}'] -> {ef['events']}")
            for d in ef['details']:
                for h in d['handlers']:
                    if h['selector']:
                        print(f"   -> on('{d['event']}', '{h['selector']}')")
                    else:
                        print(f"   -> on('{d['event']}'): {h['code'][:60]}...")
        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
