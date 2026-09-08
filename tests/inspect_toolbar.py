import asyncio
import json
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state=r'C:\Users\artce\scripts\state.json')
        page = await ctx.new_page()
        await page.goto('https://gym.dga.sinica.edu.tw/reservation.html')
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)

        nav_info = await page.evaluate('''() => {
            const btns = Array.from(document.querySelectorAll('.calendar__toolbar button, .calendar__toolbar a, .calendar__toolbar input, .calendar__month, .calendar__month-wrapper, .calendar__header *')).map(el => ({
                tag: el.tagName,
                text: el.innerText ? el.innerText.trim() : '',
                class: el.className,
                id: el.id,
                name: el.getAttribute('name') || '',
                onclick: el.getAttribute('onclick') || '',
                outer: el.outerHTML
            }));
            return btns;
        }''')
        print(f"Found {len(nav_info)} elements:")
        for b in nav_info:
            print(json.dumps(b, ensure_ascii=False))
        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
