import asyncio
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state=r"C:\Users\artce\scripts\state.json")
        page = await ctx.new_page()
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
        await page.wait_for_load_state("networkidle")
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)

        # Inspect day items in #js-v1
        res = await page.evaluate('''
            () => {
                const list = [];
                const sec = document.querySelector('#js-v1');
                sec.querySelectorAll('.calendar__day-item').forEach((day, idx) => {
                    const dayText = day.querySelector('.calendar__day-text');
                    const text = dayText ? dayText.innerText : null;
                    const html = dayText ? dayText.outerHTML : null;
                    const slots = [];
                    day.querySelectorAll('.timeline__identity').forEach(s => {
                        slots.push({ title: s.getAttribute('title'), text: s.innerText, cls: s.className });
                    });
                    list.push({ idx, text, html, slotsCount: slots.length, slots: slots.filter(s => s.title && (s.title.includes('17:00') || s.title.includes('18:00'))) });
                });
                return list;
            }
        ''')
        for r in res:
            print(f'Day idx={r["idx"]}, text={repr(r["text"])}, html={repr(r["html"])}')
            for s in r["slots"]:
                print(f'   -> {s}')
        
        # Test Playwright locator on day 05 with precise start time
        print("\n--- Testing Playwright Locators with precise slot prefix ---")
        l1 = page.locator('#js-v1 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="17:00~"], #js-v1 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="17:00 ~"]')
        print('Count for 17:00~ on day 05:', await l1.count())
        if await l1.count() > 0:
            print('Text for 17:00~:', repr(await l1.first.inner_text()))
            print('Title for 17:00~:', repr(await l1.first.get_attribute('title')))
            print('Class for 17:00~:', repr(await l1.first.get_attribute('class')))
            
        l2 = page.locator('#js-v1 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="18:00~"], #js-v1 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="18:00 ~"]')
        print('Count for 18:00~ on day 05:', await l2.count())
        if await l2.count() > 0:
            print('Text for 18:00~:', repr(await l2.first.inner_text()))
            print('Title for 18:00~:', repr(await l2.first.get_attribute('title')))
            print('Class for 18:00~:', repr(await l2.first.get_attribute('class')))

        await b.close()

if __name__ == '__main__':
    asyncio.run(test())
