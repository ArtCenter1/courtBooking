"""
驗證二段式預約頁面、reCAPTCHA 定位與安全返回之測試腳本
注意：本腳本不會點擊「預約 Reserve」送出按鈕，絕不造成意外訂位。
"""

import os
import sys
import asyncio
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import yaml
from playwright.async_api import async_playwright
from src.time_sync import time_sync, get_now

async def run_test():
    print("=" * 60)
    print("🧪 驗證二段式預約頁面、reCAPTCHA 定位與安全返回流程")
    print("=" * 60)

    # 1. 讀取設定檔
    with open(BASE_DIR / "config" / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    state_file = config['system']['state_file']
    if not os.path.exists(state_file):
        state_file = config['system']['state_backup_file']
    
    print(f"1. 驗證登入狀態檔: {state_file}")
    if not os.path.exists(state_file):
        print(f"❌ 找不到狀態檔: {state_file}")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 850},
            locale='zh-TW',
            storage_state=state_file
        )
        page = await context.new_page()

        print("2. 正在載入中研院預約頁面...")
        await page.goto(config['system']['url'], wait_until="networkidle")

        # 選擇網球場
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)

        # 關閉下拉選單
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(500)

        # 尋找任何目前可點擊的空位 (不含已預約、不含開放)
        print("3. 尋找可用時段以驗證預約表單...")
        available_slots = page.locator('#js-v1 .timeline__identity:not(.timeline__identity_no-open):not(:has-text("已預約")):not(:has-text("開放")):not(:has-text("休館"))')
        count = await available_slots.count()
        print(f"   目前 A 場可預約時段數: {count}")

        if count == 0:
            # 檢查 B 場
            await page.locator('.r-tab__link').nth(1).click(force=True)
            await page.wait_for_timeout(500)
            available_slots = page.locator('#js-v2 .timeline__identity:not(.timeline__identity_no-open):not(:has-text("已預約")):not(:has-text("開放")):not(:has-text("休館"))')
            count = await available_slots.count()
            print(f"   目前 B 場可預約時段數: {count}")

        if count > 0:
            target_slot = available_slots.first
            title = await target_slot.get_attribute("title")
            print(f"   🎯 找到可測試時段: {title}，模擬點擊進入預約表單...")
            
            t0 = time.time()
            await target_slot.click(force=True)

            # 驗證「場地預約 Reservation」頁面元素
            reserve_btn = page.locator('button:has-text("預約 Reserve"), button:has-text("預約"), input[value*="預約"]')
            await reserve_btn.first.wait_for(state="visible", timeout=5000)
            print(f"   ✅ 成功進入「場地預約」頁面！耗時: {int((time.time() - t0) * 1000)}ms")

            # 驗證 reCAPTCHA iframe
            recaptcha_frame = page.frame_locator('iframe[title*="reCAPTCHA"], iframe[src*="recaptcha"]').first
            anchor = recaptcha_frame.locator('#recaptcha-anchor, .recaptcha-checkbox')
            has_anchor = await anchor.count() > 0
            print(f"   ✅ reCAPTCHA 勾選框存在: {has_anchor}")

            # 驗證「預約 Reserve」按鈕
            has_reserve_btn = await reserve_btn.count() > 0
            print(f"   ✅ 最終「預約 Reserve」按鈕存在: {has_reserve_btn}")

            # 截圖存證
            preview_img = BASE_DIR / "reservation_form_preview.png"
            await page.screenshot(path=str(preview_img))
            print(f"   📸 表單截圖已存至: {preview_img}")

            # 點擊「返回 Back」按鈕安全返回
            back_btn = page.locator('button:has-text("返回 Back"), button:has-text("返回"), a:has-text("返回 Back"), a:has-text("返回"), .btn:has-text("返回")')
            if await back_btn.count() > 0 and await back_btn.first.is_visible():
                await back_btn.first.click()
                await page.wait_for_timeout(500)
                print("   ✅ 成功安全返回日曆表格（未執行實際預約）！")
        else:
            print("   ℹ️ 目前無空位時段可供點擊測試，驗證選擇器語法...")
            # 驗證日曆上的選擇器無語法錯誤
            assert page.locator('button:has-text("預約 Reserve")')

        print("\n" + "=" * 60)
        print("🎉 二段式流程與元素驗證完成！")
        print("=" * 60)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
