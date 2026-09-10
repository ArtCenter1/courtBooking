import asyncio
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

async def test():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context()
        page = await ctx.new_page()
        await page.goto('https://gym.dga.sinica.edu.tw/reservation.html', wait_until='networkidle')
        print('Initial URL:', page.url)
        
        login_btn = page.locator('a:has-text("登入")').first
        print('Login link count:', await login_btn.count())
        await login_btn.click()
        await page.wait_for_timeout(2000)
        
        print('URL after click login:', page.url)
        print('Pages count:', len(ctx.pages))
        for i, pg in enumerate(ctx.pages):
            print(f'Page {i}: {pg.url}')
            
        await b.close()

if __name__ == "__main__":
    asyncio.run(test())
