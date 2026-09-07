import asyncio
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state=r'C:\Users\artce\scripts\state.json')
        page = await ctx.new_page()
        await page.goto('https://gym.dga.sinica.edu.tw/reservation.html')
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        
        info = await page.evaluate('''() => {
            const h = document.querySelectorAll('h1, h2, h3, h4, h5, .title, [class*="title"], [class*="month"]');
            return Array.from(h).map(el => ({ tag: el.tagName, cls: el.className, text: el.innerText.trim() })).filter(x => x.text.length > 0 && x.text.length < 50);
        }''')
        print("Titles found:", info)
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
