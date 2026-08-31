import asyncio
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state=r"C:\Users\artce\scripts\state.json")
        page = await ctx.new_page()
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
        await page.wait_for_load_state("networkidle")
        
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        
        tabs = await page.locator('.r-tab__link').all_inner_texts()
        print('Tabs:', tabs)
        
        day_items = await page.locator('.calendar__day-item').all()
        print('Total .calendar__day-item count:', len(day_items))
        
        # Let's inspect the surrounding table structure
        table_info = await page.evaluate("""
            () => {
                const tables = [];
                document.querySelectorAll('.r-tab__content, .calendar, table').forEach((el, idx) => {
                    tables.push({
                        idx: idx,
                        tagName: el.tagName,
                        className: el.className,
                        id: el.id,
                        text: el.innerText.substring(0, 100)
                    });
                });
                return tables;
            }
        """)
        print('Containers:', table_info[:5])
        
        # Let's inspect each day-item that has '05'
        day05_details = await page.evaluate("""
            () => {
                const list = [];
                document.querySelectorAll('.calendar__day-item').forEach((item, idx) => {
                    if (item.innerText.includes('05')) {
                        const slots = [];
                        item.querySelectorAll('.timeline__identity').forEach(s => {
                            slots.push({
                                title: s.getAttribute('title'),
                                text: s.innerText,
                                class: s.className
                            });
                        });
                        list.push({
                            index: idx,
                            parentClass: item.parentElement ? item.parentElement.className : '',
                            slots: slots
                        });
                    }
                });
                return list;
            }
        """)
        for d in day05_details:
            print(f"Day05 block idx={d['index']}, parent={d['parentClass']}")
            for s in d['slots']:
                if '17:00' in s['title'] or '18:00' in s['title'] or '20:00' in s['title']:
                    print(f"   -> title={s['title']}, text={s['text']}, class={s['class']}")
        
        await b.close()

if __name__ == '__main__':
    asyncio.run(inspect())
