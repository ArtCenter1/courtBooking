# save_state.py - 使用檔案訊號等待登入完成
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

FLAG_FILE = Path(r"C:\Users\artce\scripts\login_done.flag")
STATE_FILE = Path(r"C:\Users\artce\scripts\state.json")

async def main():
    # 清除舊的旗標檔
    if FLAG_FILE.exists():
        FLAG_FILE.unlink()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
        
        print("=== 瀏覽器已開啟，請在視窗中完成登入 ===")
        print(f"登入完成後，請在資料夾建立空檔案：{FLAG_FILE}")
        print("  (可在總管中右鍵 > 新增 > 文字文件，命名為 login_done.flag)")
        print("腳本偵測到檔案後，會自動儲存 state.json 並關閉瀏覽器。")
        
        # 輪詢旗標檔
        while not FLAG_FILE.exists():
            await asyncio.sleep(1)
            # 檢查瀏覽器是否被手動關閉
            if len(context.pages) == 0:
                print("瀏覽器已被關閉，中止儲存。")
                await browser.close()
                return
        
        # 偵測到旗標檔，儲存狀態
        await context.storage_state(path=str(STATE_FILE))
        FLAG_FILE.unlink()  # 清除旗標
        print(f"✅ 登入狀態已儲存至 {STATE_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())