"""
save_state.py - 登入並儲存 Session 狀態 (state.json)
支援：
1. 忽略 SSL 憑證警告 (ignore_https_errors=True)
2. 直接前往登入頁面 (https://gym.dga.sinica.edu.tw/login.html)
3. 視窗最大化並置頂 (start-maximized)
4. 多重確認機制：
   - 方式 A: 自動偵測登入成功（頁面出現「登出」）
   - 方式 B: 使用者登入後在終端機按 [Enter]
   - 方式 C: 支援傳統 login_done.flag 檔案訊號
"""

import asyncio
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

FLAG_FILE = Path(r"C:\Users\artce\scripts\login_done.flag")
TARGET_PATHS = [
    Path(r"C:\Users\artce\scripts\state.json"),
    Path(__file__).resolve().parent / "state.json"
]

async def wait_user_enter():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, input)

async def main():
    if FLAG_FILE.exists():
        try:
            FLAG_FILE.unlink()
        except Exception:
            pass

    print("==========================================")
    print("🔑 中研院體育館系統 - 登入狀態儲存工具")
    print("==========================================")
    print("🚀 正在啟動 Chrome 瀏覽器視窗...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        context = await browser.new_context(
            no_viewport=True,
            ignore_https_errors=True,
            locale='zh-TW'
        )
        page = await context.new_page()
        
        target_url = "https://gym.dga.sinica.edu.tw/login.html"
        print(f"🌐 前往登入頁面: {target_url}")
        try:
            await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"⚠️ 載入登入頁提示: {e}，改往首頁...")
            await page.goto("https://gym.dga.sinica.edu.tw/reservation.html", timeout=30000)

        await page.bring_to_front()
        
        print("\n" + "="*50)
        print("👉 請在跳出的瀏覽器視窗中輸入帳號、密碼並完成登入。")
        print("💡 完成登入後，您可以：")
        print("   1. 回到這個命令列視窗，按 [Enter] 鍵儲存")
        print("   2. 或只要頁面跳轉並偵測到「登出」，系統也會自動儲存！")
        print("="*50 + "\n")

        # 啟動並行監聽：自動偵測 / 按 Enter / 旗標檔 / 瀏覽器關閉
        enter_task = asyncio.create_task(wait_user_enter())
        
        save_triggered = False
        while True:
            # 檢查 1: 使用者按了 Enter
            if enter_task.done():
                print("⌨️ 收到使用者 Enter 鍵確認！")
                save_triggered = True
                break

            # 檢查 2: 傳統 flag 檔
            if FLAG_FILE.exists():
                print("🚩 偵測到 login_done.flag 旗標！")
                save_triggered = True
                break

            # 檢查 3: 瀏覽器是否被手動關閉
            if len(context.pages) == 0:
                print("⚠️ 瀏覽器已被關閉。")
                break

            # 檢查 4: 自動偵測所有分頁是否已出現「登出」
            for pg in context.pages:
                try:
                    t = await pg.inner_text("body")
                    if "登出" in t or "Log out" in t or "Logout" in t:
                        print("🎉 自動偵測到登入成功（已識別「登出」狀態）！")
                        save_triggered = True
                        break
                except Exception:
                    pass

            if save_triggered:
                break

            await asyncio.sleep(0.8)

        if save_triggered:
            print("\n💾 正在擷取並儲存登入憑證 (state.json)...")
            await asyncio.sleep(1)  # 確保 cookie 寫入
            for pth in TARGET_PATHS:
                try:
                    pth.parent.mkdir(parents=True, exist_ok=True)
                    await context.storage_state(path=str(pth))
                    print(f"✅ 成功儲存登入狀態至: {pth}")
                except Exception as e:
                    print(f"⚠️ 儲存至 {pth} 異常: {e}")
            print("\n✨ 登入憑證更新大功告成！瀏覽器將在 2 秒後關閉。")
            await asyncio.sleep(2)
        else:
            print("❌ 未完成登入狀態儲存。")

        if FLAG_FILE.exists():
            try:
                FLAG_FILE.unlink()
            except Exception:
                pass

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
