import asyncio
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_nav():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state=r'C:\Users\artce\scripts\state.json')
        page = await ctx.new_page()
        await page.goto('https://gym.dga.sinica.edu.tw/reservation.html')
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)

        # 初始月份
        m1 = await page.locator('.calendar__month').first.inner_text()
        days_count1 = await page.locator('#js-v1 .calendar__day-item').count()
        print(f"Initial: month={m1}, days={days_count1}")

        # 測試點擊「當月」
        current_month_btn = page.locator('#js-v1 button:has-text("當月"), .calendar__current-month').first
        print(f"Clicking '當月'...")
        await current_month_btn.click()
        await page.wait_for_timeout(2000)
        m2 = await page.locator('.calendar__month').first.inner_text()
        days_count2 = await page.locator('#js-v1 .calendar__day-item').count()
        print(f"After '當月': month={m2}, days={days_count2}")

        # 測試點擊「下個月」
        next_month_btn = page.locator('#js-v1 button[title="下個月"], .calendar__next-month').first
        print(f"Clicking '下個月'...")
        await next_month_btn.click()
        await page.wait_for_timeout(2000)
        m3 = await page.locator('.calendar__month').first.inner_text()
        days_count3 = await page.locator('#js-v1 .calendar__day-item').count()
        print(f"After '下個月': month={m3}, days={days_count3}")

        # 測試點擊「上個月」
        prev_month_btn = page.locator('#js-v1 button[title="上個月"], .calendar__last-month').first
        print(f"Clicking '上個月'...")
        await prev_month_btn.click()
        await page.wait_for_timeout(2000)
        m4 = await page.locator('.calendar__month').first.inner_text()
        days_count4 = await page.locator('#js-v1 .calendar__day-item').count()
        print(f"After '上個月': month={m4}, days={days_count4}")

        # 測試切回「兩週內」
        two_weeks_btn = page.locator('#js-v1 button:has-text("兩週內"), .calendar__two-weeks').first
        print(f"Clicking '兩週內'...")
        await two_weeks_btn.click()
        await page.wait_for_timeout(2000)
        m5 = await page.locator('.calendar__month').first.inner_text()
        days_count5 = await page.locator('#js-v1 .calendar__day-item').count()
        print(f"After '兩週內': month={m5}, days={days_count5}")

        await b.close()

if __name__ == "__main__":
    asyncio.run(test_nav())
