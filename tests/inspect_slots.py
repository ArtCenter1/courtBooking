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
        
        slots = await page.evaluate('''() => {
            const res = [];
            document.querySelectorAll('.timeline__identity').forEach(el => {
                res.push({
                    title: el.getAttribute('title'),
                    text: el.innerText.trim(),
                    className: el.className
                });
            });
            return res;
        }''')
        
        print("Total slots found:", len(slots))
        for s in slots:
            if '已預約' not in s['text']:
                print("NON-BOOKED SLOT:", s)
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
