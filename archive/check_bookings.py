# check_bookings.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-TW',
            storage_state=r"C:\Users\artce\scripts\state.json"
        )
        page = await context.new_page()
        try:
            # 1. 進入預約頁面
            await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
            await page.wait_for_load_state("networkidle")
            
            # 2. 尋找「我的預約」或預約列表標籤
            # 有些系統會有一個 tab 或按鈕點擊顯示預約紀錄
            # 或者直接在畫面上看 08/29 的時段是不是已經變成「已預約」且是自己的帳號
            # 讓我們截圖並印出頁面上的關鍵內容
            print("正在選取網球場...")
            venue_label = page.locator('label:has-text("網球場 / Tennis court")')
            await venue_label.click()
            await page.wait_for_timeout(500)
            venue_option = page.locator('li[data-label="網球場 / Tennis court"]')
            await venue_option.click()
            await page.wait_for_timeout(1000)
            
            print("正在搜尋 08/29...")
            # 我們可以在畫面上看
            search_button = page.locator('text=搜尋 Search')
            await search_button.click()
            await page.wait_for_timeout(3000)
            
            # 選擇網球場 A
            tab_links = page.locator('.r-tab__link')
            await tab_links.first.wait_for(state="visible", timeout=5000)
            await tab_links.first.click()
            await page.wait_for_timeout(2000)
            
            # 讀取 14:00~15:00 和 15:00~16:00 的 class
            timeline_items = await page.locator('.calendar__day-item .calendar__detail .timeline__identity').all()
            for item in timeline_items:
                title = await item.get_attribute('title')
                class_attr = await item.get_attribute('class')
                if title and ("14:00~15:00" in title or "15:00~16:00" in title):
                    print(f"時段: {title} | 屬性: {class_attr}")
                    
            await page.screenshot(path="booking_status.png")
            print("📸 已儲存目前狀態截圖 booking_status.png")
            
        except Exception as e:
            print(f"發生錯誤: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())