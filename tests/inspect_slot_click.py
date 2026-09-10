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
        page.on('console', lambda msg: print('BROWSER CONSOLE:', msg.text))
        page.on('dialog', lambda d: print('DIALOG:', d.message))
        
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        
        # Get all venue options
        venue_dropdown = page.locator('label:has-text("網球場")')
        await venue_dropdown.click()
        await page.wait_for_timeout(500)
        
        venue_options = await page.evaluate('''() => {
            const list = [];
            document.querySelectorAll('li[data-label]').forEach(li => {
                list.push(li.getAttribute('data-label'));
            });
            return list;
        }''')
        print("Available venues:", venue_options)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        found_slot = None
        for v in venue_options:
            print(f"Checking venue: {v}...")
            await venue_dropdown.click()
            await page.wait_for_timeout(300)
            await page.locator(f'li[data-label="{v}"]').click()
            await page.wait_for_timeout(1000)
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)

            # Check if any slot has cursor: pointer
            pointers = await page.evaluate('''() => {
                const res = [];
                document.querySelectorAll('.timeline__identity').forEach(s => {
                    const style = window.getComputedStyle(s);
                    if (style.cursor === 'pointer' && !s.innerText.includes('已預約')) {
                        res.push({
                            title: s.getAttribute('title'),
                            text: s.innerText.trim(),
                            className: s.className
                        });
                    }
                });
                return res;
            }''')
            if pointers:
                print(f"🎉 FOUND OPEN SLOTS in {v}: {len(pointers)} slots!")
                for p_slot in pointers[:3]:
                    print("  ->", p_slot)
                found_slot = (v, pointers[0])
                break
            else:
                print(f"  No open slots in {v}.")

        await b.close()

if __name__ == "__main__":
    asyncio.run(inspect())
