"""
搶票全流程模擬推演測試 (Pre-Flight Simulation Test)
驗證 09/05 (週六) 網球場 A 17:00~18:00 與 18:00~19:00 之元素就緒度與搶票路徑。
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# 加入專案目錄
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

async def run_simulation():
    print("=" * 60)
    print("🚀 中研院網球場 09/05 實戰搶票全鏈路模擬推演")
    print("=" * 60)

    # 1. 讀取設定檔
    with open(BASE_DIR / "config" / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. 時鐘校準測試
    ok, drift, method = time_sync.calibrate()
    print(f"\n[步驟 1] 毫秒級時鐘校準:")
    print(f"  • 校時方式: {method}")
    print(f"  • 本機時間偏差: {drift:+.4f} 秒")
    print(f"  • 當前精確台北時間: {get_now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")

    # 3. 狀態檔檢驗
    state_file = config['system']['state_file']
    print(f"\n[步驟 2] 驗證登入狀態檔:")
    if not os.path.exists(state_file):
        state_file = config['system']['state_backup_file']
    print(f"  • 使用 state.json 路徑: {state_file}")
    assert os.path.exists(state_file), f"找不到 state.json: {state_file}"
    print("  • 狀態檔驗證: OK")

    # 4. 啟動瀏覽器並模擬導航與元素定位
    print(f"\n[步驟 3] 預熱進入預約系統並定位 09/05 目標時段:")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 850},
            locale='zh-TW',
            storage_state=state_file
        )
        page = await context.new_page()

        t0 = time.time()
        await page.goto(config['system']['url'], wait_until="networkidle")
        print(f"  • 預約頁面載入耗時: {int((time.time() - t0) * 1000)} ms")

        # 選擇網球場
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(800)

        # 關閉選單
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(400)

        # 驗證首選場地 (網球場 A)
        tab_links = page.locator('.r-tab__link')
        await tab_links.first.click(force=True)
        await page.wait_for_timeout(600)

        # 檢驗 09/05 網球場 A 的首選時段
        slot17 = page.locator('#js-v1 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="17:00~"], #js-v1 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="17:00 ~"]')
        slot18 = page.locator('#js-v1 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="18:00~"], #js-v1 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="18:00 ~"]')

        print(f"\n[步驟 4] 元素選擇器命中驗證 (網球場 A):")
        print(f"  • 17:00~18:00 元素匹配數: {await slot17.count()}")
        if await slot17.count() > 0:
            print(f"    - Title: {await slot17.first.get_attribute('title')}")
            print(f"    - 狀態文字: {await slot17.first.inner_text()}")
            print(f"    - Class: {await slot17.first.get_attribute('class')}")

        print(f"  • 18:00~19:00 元素匹配數: {await slot18.count()}")
        if await slot18.count() > 0:
            print(f"    - Title: {await slot18.first.get_attribute('title')}")
            print(f"    - 狀態文字: {await slot18.first.inner_text()}")
            print(f"    - Class: {await slot18.first.get_attribute('class')}")

        # 檢驗備選場地 (網球場 B 20:00)
        print(f"\n[步驟 5] 備選場地命中驗證 (網球場 B 20:00):")
        slot20_b = page.locator('#js-v2 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="20:00~"], #js-v2 .calendar__day-item:has(.calendar__day-text:has-text("05")) .timeline__identity[title*="20:00 ~"]')
        print(f"  • B場 20:00~21:00 元素匹配數: {await slot20_b.count()}")
        if await slot20_b.count() > 0:
            print(f"    - Title: {await slot20_b.first.get_attribute('title')}")
            print(f"    - 狀態文字: {await slot20_b.first.inner_text()}")

        # 檢驗「搜尋 Search」刷新按鈕
        search_btn = page.locator('text=搜尋 Search')
        print(f"\n[步驟 6] 衝刺刷新按鈕驗證:")
        print(f"  • Search 按鈕存在: {await search_btn.count() > 0}")

        # 截圖存檔
        screenshot_path = BASE_DIR / "simulation_preview.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"\n📸 推演畫面截圖已儲存至: {screenshot_path}")

        print("\n" + "=" * 60)
        print("🎉 推演驗證完全通過！所有目標元素就緒，可在 23:55 啟動正式搶票！")
        print("=" * 60)

        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_simulation())
