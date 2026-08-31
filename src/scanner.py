"""
頁面時段掃描與解析模組 (Calendar Scanner)
專門解析中研院體育館預約日曆表格，識別指定日期的時段狀態（已預約/即將開放/可預約）。
"""

import json
from playwright.async_api import async_playwright

class CalendarScanner:
    def __init__(self, config, auth_manager, notifier):
        self.config = config
        self.auth = auth_manager
        self.notifier = notifier

    async def scan_day_slots(self, target_day_num="05", court="A", headless=True):
        """
        掃描指定場地在特定日期（如 05 日）的所有時段狀態
        """
        state_file = self.auth.state_file
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                locale='zh-TW',
                storage_state=state_file
            )
            page = await context.new_page()
            try:
                target_url = self.config['system']['url']
                await page.goto(target_url, wait_until="networkidle")
                
                # 選擇網球場
                await page.locator('label:has-text("網球場 / Tennis court")').click()
                await page.locator('li[data-label="網球場 / Tennis court"]').click()
                await page.wait_for_timeout(1000)

                # 收起下拉選單
                await page.keyboard.press("Escape")
                await page.locator('body').click(position={"x": 10, "y": 10})
                await page.wait_for_timeout(500)

                # 切換場地 (A / B)
                tab_links = page.locator('.r-tab__link')
                sec_id = "#js-v1" if court == 'A' else "#js-v2"
                if court == 'A':
                    await tab_links.first.click(force=True)
                else:
                    await tab_links.nth(1).click(force=True)
                await page.wait_for_timeout(1000)

                # 透過 evaluate 抓取指定 section 的 day-item
                scan_result = await page.evaluate("""
                    ({ dayTarget, secId }) => {
                        const sec = document.querySelector(secId) || document;
                        const days = sec.querySelectorAll('.calendar__day-item');
                        const matchedDays = [];
                        
                        days.forEach(day => {
                            const headerEl = day.querySelector('.calendar__day-header') || day.querySelector('.calendar__day-text');
                            const headerText = day.innerText.split('\\n')[0] || '';
                            const dayTextEl = day.querySelector('.calendar__day-text');
                            const dayNum = dayTextEl ? dayTextEl.innerText.trim() : '';
                            
                            // 檢查是否符合目標日期 (例如 05 或 5)
                            const isMatch = (dayNum === dayTarget || dayNum === String(parseInt(dayTarget, 10)) || headerText.includes(dayTarget));
                            
                            const slotItems = [];
                            day.querySelectorAll('.timeline__identity').forEach(slot => {
                                const title = slot.getAttribute('title') || '';
                                const className = slot.className || '';
                                const text = slot.innerText ? slot.innerText.trim() : '';
                                
                                slotItems.push({
                                    title: title,
                                    text: text,
                                    class: className,
                                    isNonSinica: className.includes('non-sinica'),
                                    isBooked: text.includes('已預約'),
                                    isOpenPending: text.includes('開放') || className.includes('no-open'),
                                    isClickable: !text.includes('已預約') && !className.includes('disabled')
                                });
                            });
                            
                            matchedDays.push({
                                dayNum: dayNum,
                                rawHeader: headerText,
                                isTarget: isMatch,
                                slots: slotItems
                            });
                        });
                        return matchedDays;
                    }
                """, {"dayTarget": str(target_day_num), "secId": sec_id})

                await browser.close()
                return scan_result
            except Exception as e:
                self.notifier.log(f"❌ 掃描過程出錯: {e}")
                await browser.close()
                return []
