"""
毫秒級高可靠搶票引擎 (Sniper Engine) - 專屬中研院雙場地極速預約
針對 09/05 (Sa 05) 網球場 A (17:00-18:00, 18:00-19:00) 及網球場 B (20:00-21:00) 特化
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from src.time_sync import time_sync, get_now, TAIPEI_TZ

class Sniper:
    def __init__(self, config, auth_manager, notifier):
        self.config = config
        self.auth = auth_manager
        self.notifier = notifier
        self.target_date = config['target']['date']            # "09/05"
        self.target_day_num = str(config['target']['day_num']) # "05"
        self.primary_slots = config['target']['primary_slots'] # ["17:00", "18:00"]
        self.court_order = config['target']['court_order']     # ["A", "B"]
        self.min_hour = config['target']['fallback_time_range']['min_hour']
        self.max_hour = config['target']['fallback_time_range']['max_hour']
        self.screenshot_dir = config['system'].get('screenshot_dir', r"C:\Users\artce\scripts")

    def _get_court_section_id(self, court_name):
        return "#js-v1" if court_name.upper() == "A" else "#js-v2"

    async def try_book_slot(self, page, court_name, slot_prefix, day_num, timeout_ms=2000):
        """
        嘗試鎖定指定場地、指定日期與時段，並極速點擊確認預約。
        返回 (True, message) 或 (False, message)
        """
        section_id = self._get_court_section_id(court_name)
        try:
            # 精準定位：指定場地 section -> 指定日期 block -> 指定時段 (以 slot_prefix~ 比對開頭時段，避免混淆)
            slot_locator = page.locator(
                f'{section_id} .calendar__day-item:has(.calendar__day-text:has-text("{day_num}")) .timeline__identity[title*="{slot_prefix}~"], '
                f'{section_id} .calendar__day-item:has(.calendar__day-text:has-text("{day_num}")) .timeline__identity[title*="{slot_prefix} ~"]'
            )
            
            if await slot_locator.count() == 0:
                # 備用容錯定位
                slot_locator = page.locator(
                    f'{section_id} .timeline__identity[title*="{slot_prefix}~"], '
                    f'{section_id} .timeline__identity[title*="{slot_prefix} ~"]'
                )

            if await slot_locator.count() == 0:
                return False, f"[{court_name}場] 未找到時段: {slot_prefix}"

            target_el = slot_locator.first
            text = (await target_el.inner_text()).strip()
            class_name = await target_el.get_attribute('class') or ''
            
            # 若標記為已預約或尚未開放 (09/01開放 / no-open)，代表該時段目前不可點，立即跳過以加速下一輪刷新
            if "已預約" in text:
                return False, f"[{court_name}場] 時段已被預約 ({slot_prefix})"
            if "開放" in text or "no-open" in class_name:
                return False, f"[{court_name}場] 時段尚未釋出開放 ({slot_prefix})"

            # 點擊時段觸發預約對話框
            t0 = time.time()
            await target_el.click(force=True)
            
            # 等待「確認預約」按鈕出現並點擊
            confirm_btn = page.locator('button:has-text("確認預約"), button:has-text("確認")')
            await confirm_btn.wait_for(state="visible", timeout=timeout_ms)
            await confirm_btn.first.click()
            elapsed_ms = int((time.time() - t0) * 1000)
            
            # 短暫等待 PrimeFaces AJAX 完成
            await page.wait_for_timeout(350)
            return True, f"[{court_name}場] 成功點擊預約: {slot_prefix} (耗時 {elapsed_ms}ms)"
        except Exception as e:
            return False, f"[{court_name}場] 預約嘗試異常 ({slot_prefix}): {e}"

    async def run_snipe_task(self, dry_run=False, dry_run_seconds=5):
        """
        執行完整搶票流程
        """
        self.notifier.log("==========================================")
        self.notifier.log(f"🎯 啟動搶票核心 | 目標日期: {self.target_date} (日: {self.target_day_num})")
        self.notifier.log(f"📋 首選目標: 網球場 A {self.primary_slots}")
        self.notifier.log(f"📋 備選目標: {self.min_hour}:00~{self.max_hour}:00 零星釋出時段 (網球場 A/B)")
        self.notifier.log("==========================================")

        # 1. 毫秒級時間校準
        ok, drift, method = time_sync.calibrate()
        self.notifier.log(f"⏱️ 時鐘校準完成: 漂移偏差 = {drift:+.3f} 秒 (校時來源: {method})")

        state_file = self.auth.state_file
        if not state_file or not os.path.exists(state_file):
            self.notifier.log(f"❌ 錯誤: 找不到登入狀態檔 ({state_file})")
            return False

        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 850},
                locale='zh-TW',
                storage_state=state_file
            )
            page = await context.new_page()

            try:
                # 2. 預熱與頁面載入
                self.notifier.log(f"🌐 正在載入預約系統: {self.config['system']['url']}")
                await page.goto(self.config['system']['url'], wait_until="networkidle")

                # 選擇網球場
                self.notifier.log("🎾 預選「網球場 / Tennis court」...")
                await page.locator('label:has-text("網球場")').click()
                await page.locator('li[data-label="網球場 / Tennis court"]').click()
                await page.wait_for_timeout(1000)

                # 收起下拉選單
                await page.keyboard.press("Escape")
                await page.locator('body').click(position={"x": 10, "y": 10})
                await page.wait_for_timeout(500)

                # 預選網球場 A 標籤
                tab_links = page.locator('.r-tab__link')
                await tab_links.first.click(force=True)
                await page.wait_for_timeout(500)

                # 3. 計算 00:00:00 目標時間
                now = get_now()
                if dry_run:
                    self.notifier.log(f"🧪 【模擬推演】將在 {dry_run_seconds} 秒後模擬放票瞬間...")
                    target_time = now + timedelta(seconds=dry_run_seconds)
                else:
                    target_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    if now.hour >= 12:
                        target_time += timedelta(days=1)
                    self.notifier.log(f"⏰ 正式放票目標時間: {target_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} (校準時鐘)")

                # 高精度倒數循環
                last_print_sec = -1
                while True:
                    cur_now = get_now()
                    remaining = (target_time - cur_now).total_seconds()
                    if remaining <= 0.005:  # 提前 5ms 衝刺發動
                        break
                    
                    if remaining > 10:
                        int_rem = int(remaining)
                        if int_rem != last_print_sec and (int_rem % 30 == 0 or int_rem <= 60):
                            self.notifier.log(f"⏳ 距 00:00 放票剩餘: {int_rem // 60} 分 {int_rem % 60} 秒...")
                            last_print_sec = int_rem
                        await asyncio.sleep(0.5)
                    elif remaining > 2:
                        print(f"🔥 倒數進入衝刺區: {remaining:.2f} 秒...", end='\r', flush=True)
                        await asyncio.sleep(0.08)
                    else:
                        print(f"⚡ [極限倒數] {remaining:.3f} 秒...", end='\r', flush=True)
                        await asyncio.sleep(0.008)

                self.notifier.log("\n🔔 00:00:00 放票！發動極速預約衝刺！")
                search_btn = page.locator('text=搜尋 Search')

                success_slots = []
                max_attempts = self.config['system'].get('refresh_attempts', 40)
                refresh_interval_ms = self.config['system'].get('refresh_interval_ms', 300)

                for attempt in range(1, max_attempts + 1):
                    t_start = time.time()
                    await search_btn.click()
                    await page.wait_for_timeout(refresh_interval_ms)

                    # 第一優先：網球場 A 的首選時段 (17:00, 18:00)
                    for slot in self.primary_slots:
                        if slot in success_slots:
                            continue
                        ok, msg = await self.try_book_slot(page, "A", slot, self.target_day_num)
                        if ok:
                            self.notifier.log(f"🎉 【A 計劃成功】{msg}")
                            success_slots.append(slot)
                        else:
                            self.notifier.log(f"   [A場] {msg}")

                    # 若已全數預約成功
                    if len(success_slots) == len(self.primary_slots):
                        self.notifier.log(f"🏆 【大獲全勝】首選時段全數預約成功！時段: {success_slots}")
                        break

                    # 若前幾輪首選時段 (17:00, 18:00) 未全數獲取，啟動 14:00~17:00 零星時段撿漏
                    if attempt >= 3 and len(success_slots) < 2:
                        for idx, court in enumerate(["A", "B"]):
                            if len(success_slots) >= 2:
                                break
                            
                            # 若要掃描 B 場，先切換分頁標籤
                            if court == "B":
                                await tab_links.nth(1).click(force=True)
                                await page.wait_for_timeout(250)
                            else:
                                await tab_links.first.click(force=True)
                                await page.wait_for_timeout(150)

                            sec_id = "#js-v1" if court == "A" else "#js-v2"
                            available_titles = await page.evaluate(f"""
                                (selector) => {{
                                    const res = [];
                                    const sec = document.querySelector(selector);
                                    if (sec) {{
                                        sec.querySelectorAll('.timeline__identity').forEach(el => {{
                                            const title = el.getAttribute('title') || '';
                                            const txt = el.innerText || '';
                                            if (!txt.includes('已預約') && !txt.includes('開放') && title.includes('~')) {{
                                                res.push(title);
                                            }}
                                        }});
                                    }}
                                    return res;
                                }}
                            """, sec_id)

                            for t in available_titles:
                                prefix = t.split('~')[0].strip()
                                # 解析時段起始小時 (如 "14:00" -> 14)
                                try:
                                    slot_hour = int(prefix.split(':')[0])
                                except ValueError:
                                    continue

                                # 嚴格限制：僅考慮 14 <= hour < 17 (14:00~17:00)
                                if self.min_hour <= slot_hour < self.max_hour:
                                    slot_key = f"{court}:{prefix}"
                                    if slot_key in success_slots or prefix in success_slots:
                                        continue
                                    ok, msg = await self.try_book_slot(page, court, prefix, self.target_day_num)
                                    if ok:
                                        self.notifier.log(f"🎉 【撿漏成功】{court}場 {prefix} - {msg}")
                                        success_slots.append(slot_key)
                                        if len(success_slots) >= 2:
                                            break

                    if len(success_slots) >= 2:
                        break

                    if len(success_slots) >= 2:
                        break

                # 4. 截圖存證
                res_img = os.path.join(self.screenshot_dir, f"snipe_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                await page.screenshot(path=res_img)
                self.notifier.log(f"📸 搶票結果截圖: {res_img}")

                if success_slots:
                    self.notifier.log(f"✅ 搶票任務完成！預約時段清單: {success_slots}")
                    self.notifier.send_telegram(f"🎾 中研院網球場預約成功！\n日期: {self.target_date}\n預約成功: {', '.join(success_slots)}")
                    return True
                else:
                    self.notifier.log("❌ 本次衝刺未成功獲取目標時段。")
                    return False

            except Exception as e:
                self.notifier.log(f"❌ 嚴重例外: {e}")
                err_img = os.path.join(self.screenshot_dir, "snipe_error.png")
                await page.screenshot(path=err_img)
                return False
            finally:
                if dry_run:
                    self.notifier.log("👋 [模擬推演] 保持瀏覽器 8 秒後自動關閉...")
                    await asyncio.sleep(8)
                    await browser.close()
                else:
                    self.notifier.log("🖥️ [正式搶票] 瀏覽器視窗已保留在畫面上供您即時檢視！")
                    self.notifier.log("👉 您可以直接在該視窗操作。按 Enter 鍵或關閉視窗即可結束程式...")
                    try:
                        await asyncio.get_event_loop().run_in_executor(None, input)
                    except Exception:
                        await asyncio.sleep(3600)
                    await browser.close()
