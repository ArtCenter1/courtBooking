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
        court: "A", "B", 或 "ALL"
        """
        state_file = self.auth.state_file if hasattr(self.auth, 'state_file') else None
        
        # 準備瀏覽器 Context 參數
        context_kwargs = {
            'viewport': {'width': 1280, 'height': 800},
            'locale': 'zh-TW'
        }
        if state_file and __import__('os').path.exists(state_file):
            context_kwargs['storage_state'] = state_file

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            try:
                target_url = self.config['system']['url']
                await page.goto(target_url, wait_until="networkidle")
                
                # 選擇網球場
                await page.locator('label:has-text("網球場")').click()
                await page.locator('li[data-label="網球場 / Tennis court"]').click()
                await page.wait_for_timeout(1000)

                # 收起下拉選單
                await page.keyboard.press("Escape")
                await page.locator('body').click(position={"x": 10, "y": 10})
                await page.wait_for_timeout(500)

                # 切換場地以確保資料載入 (若選擇 ALL，依序點擊載入)
                tab_links = page.locator('.r-tab__link')
                if court == 'ALL':
                    await tab_links.first.click(force=True)
                    await page.wait_for_timeout(500)
                    await tab_links.nth(1).click(force=True)
                    await page.wait_for_timeout(500)
                else:
                    if court == 'A':
                        await tab_links.first.click(force=True)
                    else:
                        await tab_links.nth(1).click(force=True)
                    await page.wait_for_timeout(1000)

                # 透過 evaluate 抓取
                scan_result = await page.evaluate(r"""
                    ({ dayTarget, courtTarget }) => {
                        const results = {};
                        const courtsToScan = courtTarget === 'ALL' ? ['A', 'B'] : [courtTarget];
                        
                        courtsToScan.forEach(c => {
                            const secId = c === 'A' ? '#js-v1' : '#js-v2';
                            const sec = document.querySelector(secId) || document;
                            const days = sec.querySelectorAll('.calendar__day-item');
                            const matchedDays = [];
                            
                            days.forEach(day => {
                                const headerEl = day.querySelector('.calendar__day-header') || day.querySelector('.calendar__day-text');
                                const headerText = day.innerText.split('\\n')[0] || '';
                                const dayTextEl = day.querySelector('.calendar__day-text');
                                const dayNum = dayTextEl ? dayTextEl.innerText.trim() : '';
                                
                                // 檢查是否符合目標日期
                                const isMatch = (dayNum === dayTarget || dayNum === String(parseInt(dayTarget, 10)) || headerText.includes(dayTarget));
                                
                                const slotItems = [];
                                day.querySelectorAll('.timeline__identity').forEach(slot => {
                                    const title = slot.getAttribute('title') || '';
                                    const className = slot.className || '';
                                    const text = slot.innerText ? slot.innerText.trim() : '';
                                    
                                    // 解析起訖時間 e.g. "17:00~18:00" 或 "17~18"
                                    let startTime = "";
                                    const timeMatch = title.match(/(\d{2}):\d{2}~/);
                                    if (timeMatch) {
                                        startTime = timeMatch[1] + ":00";
                                    } else if (text.match(/(\d{2})~\d{2}/)) {
                                        startTime = text.match(/(\d{2})~\d{2}/)[1] + ":00";
                                    }
                                    
                                    const isBooked = text.includes('已預約');
                                    // 修正 isOpenPending: 不再誤判 'no-open'，只根據文字判斷是否為「開放」
                                    const isOpenPending = text.includes('開放');
                                    // 可預約: 非預約滿、非即將開放、有明確時間格式
                                    const isAvailable = (!isBooked && !isOpenPending && (text.includes('~') || startTime !== ""));
                                    
                                    slotItems.push({
                                        title: title,
                                        text: text,
                                        startTime: startTime,
                                        class: className,
                                        isBooked: isBooked,
                                        isOpenPending: isOpenPending,
                                        isAvailable: isAvailable
                                    });
                                });
                                
                                matchedDays.push({
                                    dayNum: dayNum,
                                    rawHeader: headerText,
                                    isTarget: isMatch,
                                    slots: slotItems
                                });
                            });
                            results[c] = matchedDays;
                        });
                        return courtTarget === 'ALL' ? results : results[courtTarget];
                    }
                """, {"dayTarget": str(target_day_num), "courtTarget": court})

                await browser.close()
                return scan_result
            except Exception as e:
                self.notifier.log(f"❌ 掃描過程出錯: {e}")
                await browser.close()
                return {} if court == 'ALL' else []

    async def scan_full_calendar(self, headless=True, view_mode: str = "two_weeks", nav_action: str = None):
        """
        全域掃描：一次抓取完整日曆 A/B 兩場地的所有時段狀態
        view_mode: 'two_weeks' (兩週內) 或 'current_month' (當月)
        nav_action: 可選 'prev_month' (上個月), 'next_month' (下個月), 'two_weeks' (兩週內), 'current_month' (當月)
        """
        state_file = self.auth.state_file if hasattr(self.auth, 'state_file') else None
        
        context_kwargs = {
            'viewport': {'width': 1280, 'height': 800},
            'locale': 'zh-TW'
        }
        if state_file and __import__('os').path.exists(state_file):
            context_kwargs['storage_state'] = state_file

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            try:
                target_url = self.config['system']['url']
                await page.goto(target_url, wait_until="networkidle")
                
                # 選擇網球場
                await page.locator('label:has-text("網球場")').click()
                await page.locator('li[data-label="網球場 / Tennis court"]').click()
                await page.wait_for_timeout(1000)

                # 收起下拉選單
                await page.keyboard.press("Escape")
                await page.locator('body').click(position={"x": 10, "y": 10})
                await page.wait_for_timeout(500)

                # 若指定了切換動作，模擬點擊中研院官方工具列按鈕
                action_map = {
                    "prev_month": 'button[title="上個月"], .calendar__last-month',
                    "next_month": 'button[title="下個月"], .calendar__next-month',
                    "current_month": 'button:has-text("當月"), .calendar__current-month',
                    "two_weeks": 'button:has-text("兩週內"), .calendar__two-weeks'
                }
                
                if nav_action and nav_action in action_map:
                    target_btn = page.locator(f'#js-v1 {action_map[nav_action]}').first
                    if await target_btn.count() > 0:
                        await target_btn.click()
                        await page.wait_for_timeout(1500)
                elif view_mode == "current_month":
                    target_btn = page.locator('#js-v1 button:has-text("當月"), .calendar__current-month').first
                    if await target_btn.count() > 0:
                        await target_btn.click()
                        await page.wait_for_timeout(1500)

                tab_links = page.locator('.r-tab__link')
                await tab_links.first.click(force=True)
                await page.wait_for_timeout(400)
                await tab_links.nth(1).click(force=True)
                await page.wait_for_timeout(400)

                scan_result = await page.evaluate(r"""
                    () => {
                        const results = { A: [], B: [], monthTitle: '' };
                        const monthEl = document.querySelector('.calendar__month');
                        if (monthEl) {
                            results.monthTitle = monthEl.innerText.trim();
                        }
                        
                        ['A', 'B'].forEach(c => {
                            const secId = c === 'A' ? '#js-v1' : '#js-v2';
                            const sec = document.querySelector(secId) || document;
                            const days = sec.querySelectorAll('.calendar__day-item');
                            
                            days.forEach(day => {
                                const headerText = day.innerText.split('\n')[0] || '';
                                const dayTextEl = day.querySelector('.calendar__day-text');
                                const dayNum = dayTextEl ? dayTextEl.innerText.trim() : '';
                                const isToday = !!(dayTextEl && dayTextEl.classList.contains('calendar__selected-date'));
                                
                                const slotItems = [];
                                day.querySelectorAll('.timeline__identity').forEach(slot => {
                                    const title = slot.getAttribute('title') || '';
                                    const text = slot.innerText ? slot.innerText.trim() : '';
                                    const className = slot.className || '';
                                    
                                    let startTime = "";
                                    const timeMatch = title.match(/(\d{2}):\d{2}~/);
                                    if (timeMatch) {
                                        startTime = timeMatch[1] + ":00";
                                    } else if (text.match(/(\d{2})~\d{2}/)) {
                                        startTime = text.match(/(\d{2})~\d{2}/)[1] + ":00";
                                    }
                                    
                                    const isBooked = text.includes('已預約');
                                    const isOpenPending = text.includes('開放') || title.includes('開放');
                                    const isClosed = text.includes('休館') || title.includes('休館');
                                    const isAvailable = (!isBooked && !isOpenPending && !isClosed && (text.includes('~') || startTime !== ""));
                                    
                                    // 提取開放日期時間 e.g. "09/08"
                                    let openDate = "";
                                    const openMatch = (title + " " + text).match(/(\d{1,2}\/\d{1,2})/);
                                    if (openMatch) {
                                        openDate = openMatch[1];
                                    }

                                    slotItems.push({
                                        title: title,
                                        text: text,
                                        startTime: startTime,
                                        className: className,
                                        isBooked: isBooked,
                                        isOpenPending: isOpenPending,
                                        isClosed: isClosed,
                                        isAvailable: isAvailable,
                                        openDate: openDate
                                    });
                                });
                                
                                results[c].push({
                                    dayNum: dayNum,
                                    headerText: headerText,
                                    isToday: isToday,
                                    slots: slotItems
                                });
                            });
                        });
                        return results;
                    }
                """)

                await browser.close()
                return scan_result
            except Exception as e:
                self.notifier.log(f"❌ 全域掃描出錯: {e}")
                await browser.close()
                return {"A": [], "B": []}

