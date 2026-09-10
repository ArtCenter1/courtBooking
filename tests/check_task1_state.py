import asyncio
import sys
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=r"D:\My_Projects\courtBooking\data\states\state_user_1.json",
            ignore_https_errors=True
        )
        page = await context.new_page()
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", wait_until="networkidle")
        has_logout = await page.locator("text=登出").count() > 0
        print("state_user_1 Has 登出:", has_logout)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
