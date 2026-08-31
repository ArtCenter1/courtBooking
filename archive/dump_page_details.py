# dump_page_details.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-TW',
            storage_state=r"C:\Users\artce\scripts\state.json"
        )
        page = await context.new_page()
        try:
            await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
            await page.wait_for_load_state("networkidle")
            
            # 尋找所有選單、連結或按鈕中的「預約」或「我的」相關文字
            links = await page.locator('a, button, li').all()
            print("=== 頁面上的選單或按鈕 ===")
            for link in links:
                text = await link.inner_text()
                if text and ("預約" in text or "歷史" in text or "紀錄" in text or "我的" in text or "個人" in text):
                    print(f"標籤: {link.page.url} | 元素: {link} | 文字: {text.strip()}")
            
            # 尋找 08/29 這一天的具體區塊
            print("\n=== 尋找 08/29 的預約格屬性 ===")
            # 在 PrimeFaces 中，通常每天有一個單獨的 td 或 container，裡面有該天的時段。
            # 我們可以定位到含有 "08/29" 或是 "08-29" 的格子，然後看 14:00~15:00 的屬性
            day_elements = await page.locator('.calendar__day-item').all()
            for day in day_elements:
                header_text = await day.locator('.calendar__day-header').inner_text()
                if "08/29" in header_text or "29" in header_text:
                    print(f"找到日期區塊: {header_text.strip()}")
                    slots = await day.locator('.timeline__identity').all()
                    for slot in slots:
                        title = await slot.get_attribute('title')
                        class_attr = await slot.get_attribute('class')
                        inner = await slot.inner_text()
                        print(f"  時段標題: {title} | 類別: {class_attr} | 文字: {inner.strip()}")
                        
        except Exception as e:
            print(f"錯誤: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())