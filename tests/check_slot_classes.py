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
        
        slots_11 = await page.evaluate("""() => {
            const day11 = document.querySelectorAll('#js-v2 .calendar__day-item')[5]; // Day 11 is index 5
            const res = [];
            day11.querySelectorAll('.timeline__identity').forEach(el => {
                res.push({
                    text: el.innerText.trim(),
                    title: el.getAttribute('title'),
                    className: el.className,
                    html: el.outerHTML
                });
            });
            return res;
        }""")
        print("ALL SLOTS ON DAY 11 (COURT B):")
        for s in slots_11:
            print(s)

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
