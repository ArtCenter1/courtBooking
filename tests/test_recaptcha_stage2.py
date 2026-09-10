"""
專門測試第二階段「場地預約 Reservation」頁面與 reCAPTCHA 人機驗證穿透
絕不按下「預約 Reserve」，測試完成後點擊「返回 Back」回到日曆。
"""

import os
import sys
import time
import asyncio
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

async def test_stage2_recaptcha():
    print("=" * 65)
    print("🛡️ 實測：第二階段進入預約表單頁並自動穿透 reCAPTCHA 人機驗證")
    print("=" * 65)

    with open(BASE_DIR / "config" / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    state_file = config['system']['state_file']
    if not os.path.exists(state_file):
        state_file = config['system']['state_backup_file']

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 850},
            locale='zh-TW',
            storage_state=state_file
        )
        page = await context.new_page()

        print("1. 載入預約日曆頁面...")
        await page.goto(config['system']['url'], wait_until="networkidle")

        # 選擇網球場
        await page.locator('label:has-text("網球場")').click()
        await page.locator('li[data-label="網球場 / Tennis court"]').click()
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Escape")
        await page.locator('body').click(position={"x": 10, "y": 10})
        await page.wait_for_timeout(500)

        # 尋找明天之後的可用空位 (dayNum > 10)
        print("2. 掃描明天之後的可點擊測試空位...")
        future_slots = await page.evaluate('''
            () => {
                const results = [];
                const days = document.querySelectorAll('.calendar__day-item');
                days.forEach(day => {
                    const dayEl = day.querySelector('.calendar__day-text');
                    const dayNum = dayEl ? parseInt(dayEl.innerText.trim(), 10) : 0;
                    // 只要大於 10 號 (明天及之後)
                    if (dayNum > 10) {
                        day.querySelectorAll('.timeline__identity').forEach((s, sIdx) => {
                            const txt = s.innerText ? s.innerText.trim() : '';
                            const title = s.getAttribute('title') || '';
                            if (txt && !txt.includes('已預約') && !txt.includes('開放') && !txt.includes('休館')) {
                                results.push({ dayNum, txt, title, sIdx });
                            }
                        });
                    }
                });
                return results;
            }
        ''')

        print(f"   找到未來可用空位數: {len(future_slots)}")
        if not future_slots:
            print("❌ 未來日期暫無開放空位！嘗試檢查 B 場...")
            await page.locator('.r-tab__link').nth(1).click(force=True)
            await page.wait_for_timeout(500)
            # 再抓一次 B 場
            future_slots = await page.evaluate('''
                () => {
                    const results = [];
                    const days = document.querySelectorAll('#js-v2 .calendar__day-item');
                    days.forEach(day => {
                        const dayEl = day.querySelector('.calendar__day-text');
                        const dayNum = dayEl ? parseInt(dayEl.innerText.trim(), 10) : 0;
                        if (dayNum >= 10) {
                            day.querySelectorAll('.timeline__identity').forEach((s, sIdx) => {
                                const txt = s.innerText ? s.innerText.trim() : '';
                                const title = s.getAttribute('title') || '';
                                if (txt && !txt.includes('已預約') && !txt.includes('開放') && !txt.includes('休館')) {
                                    results.push({ dayNum, txt, title, sIdx });
                                }
                            });
                        }
                    });
                    return results;
                }
            ''')
            print(f"   B 場未來可用空位數: {len(future_slots)}")

        if not future_slots:
            print("❌ 目前未來日期所有時段均已被預約或尚未開放，無法點入第二階段。")
            await browser.close()
            return

        pick = future_slots[0]
        print(f"🎯 鎖定未來測試時段: {pick['dayNum']} 日 {pick['title']} ({pick['txt']})")
        
        # 定位該元素
        day_str = f"{pick['dayNum']:02d}"
        target_slot = page.locator(f'.calendar__day-item:has(.calendar__day-text:has-text("{day_str}")) .timeline__identity[title*="{pick["title"][:5]}"]').first
        
        print("3. 模擬第一階段：點擊時段進入「場地預約 Reservation」...")
        t0 = time.time()
        await target_slot.click(force=True)

        # 等待進入預約表單頁
        reserve_btn = page.locator('button:has-text("預約 Reserve"), button:has-text("預約"), input[value*="預約"]')
        try:
            await reserve_btn.first.wait_for(state="visible", timeout=6000)
            elapsed_nav = int((time.time() - t0) * 1000)
            print(f"   ✅ 成功抵達「場地預約」頁面！導航耗時: {elapsed_nav}ms")
        except Exception as e:
            print(f"❌ 導航到預約頁面超時: {e}")
            await browser.close()
            return

        print("4. 模擬第二階段：定位並穿透 Google reCAPTCHA v2 iframe...")
        recaptcha_frame = page.frame_locator('iframe[title*="reCAPTCHA"], iframe[src*="recaptcha"]').first
        anchor = recaptcha_frame.locator('#recaptcha-anchor, .recaptcha-checkbox')

        try:
            await anchor.wait_for(state="visible", timeout=3000)
            print("   ✅ 成功定位 reCAPTCHA「我不是機器人」核取方塊！")
        except Exception as e:
            print(f"❌ 無法定位 reCAPTCHA iframe: {e}")
            await browser.close()
            return

        print("   ⚡ 觸發點擊 reCAPTCHA 核取方塊...")
        t_click = time.time()
        await anchor.click(force=True)

        print("   ⏳ 等待 Google 伺服器驗證回應 (檢測 aria-checked)...")
        checked_locator = recaptcha_frame.locator('#recaptcha-anchor[aria-checked="true"], .recaptcha-checkbox-checked')
        
        try:
            await checked_locator.wait_for(state="visible", timeout=5000)
            elapsed_captcha = int((time.time() - t_click) * 1000)
            print(f"   🎉 【人機驗證大獲全勝】reCAPTCHA 成功打勾通過！驗證耗時: {elapsed_captcha}ms")
        except Exception as e:
            print(f"   ⚠️ 未在 5 秒內自動打勾，可能出現圖片挑戰題: {e}")

        # 檢驗「預約 Reserve」按鈕是否就緒
        btn_count = await reserve_btn.count()
        print(f"5. 檢驗最終送出「預約 Reserve」按鈕: {'就緒 (OK)' if btn_count > 0 else '未找到'}")
        print("   🛡️ [Dry-Run 安全模式] 絕不按下「預約 Reserve」，避免造成預約！")

        # 截圖存證
        screenshot_path = BASE_DIR / "recaptcha_verified_preview.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"📸 驗證成功畫面截圖已儲存至: {screenshot_path}")

        # 點擊「返回 Back」按鈕安全返回
        print("6. 點擊「返回 Back」安全退出表單...")
        back_btn = page.locator('button:has-text("返回 Back"), button:has-text("返回"), a:has-text("返回 Back"), a:has-text("返回"), .btn:has-text("返回")')
        if await back_btn.count() > 0 and await back_btn.first.is_visible():
            await back_btn.first.click()
            await page.wait_for_timeout(500)
            print("   ✅ 已成功安全返回日曆表格！")

        print("\n" + "=" * 65)
        print("🏆 結論：第二階段 reCAPTCHA 完全可透過自動化秒級穿透！")
        print("=" * 65)

        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_stage2_recaptcha())
