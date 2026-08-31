#!/usr/bin/env python3
"""
新版 Monitor v3：用 evaluate() 一次抓全部資料，避免逐一 locator 超時
"""
import asyncio
import os
import json
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

TAIPEI_TZ = timezone(timedelta(hours=8))
ALERT_FILE = os.path.expanduser("~/.gym_reservation_alert.json")
LOG_FILE = os.path.expanduser("~/.gym_monitor.log")

def log(msg):
    timestamp = datetime.now(TAIPEI_TZ).strftime('%H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def get_target_date():
    now = datetime.now(TAIPEI_TZ)
    return (now + timedelta(days=5)).strftime('%m/%d')

async def main():
    target_date = get_target_date()
    log(f"📅 目標日期: {target_date} (院外人士 +5 天)")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-TW',
            storage_state=r"C:\Users\artce\scripts\state.json"
        )
        page = await context.new_page()
        
        try:
            log("進入預約頁面...")
            await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
            await page.wait_for_load_state("networkidle")
            
            log("選擇網球場...")
            await page.locator('label:has-text("網球場 / Tennis court")').click()
            await page.locator('li[data-label="網球場 / Tennis court"]').click()
            await page.wait_for_timeout(3000)
            
            # 用 evaluate 一次抓所有 day-item 的 HTML
            log("批次讀取 DOM...")
            data = await page.evaluate("""
                () => {
                    const days = document.querySelectorAll('.calendar__day-item');
                    const result = [];
                    days.forEach(day => {
                        const header = day.querySelector('.calendar__day-header');
                        const headerText = header ? header.innerText.replace(/\\n/g, ' ').trim() : '';
                        const slots = [];
                        day.querySelectorAll('.timeline__identity_non-sinica').forEach(item => {
                            slots.push({
                                title: item.getAttribute('title') || '',
                                className: item.className
                            });
                        });
                        if (slots.length > 0) {
                            result.push({ header: headerText, slots: slots });
                        }
                    });
                    return result;
                }
            """)
            
            log(f"找到 {len(data)} 個有院外人士時段的日期區塊")
            log("DEBUG: 第一個日期區塊的完整 HTML：")
            html_debug = await page.evaluate("""
                () => {
                    const day = document.querySelectorAll('.calendar__day-item')[0];
                    return day ? day.innerHTML.substring(0, 500) : 'NOT FOUND';
                }
            """)
            log(f"  {html_debug}")
            
            all_target_slots = []
            for day in data:
                header = day['header']
                # 解析日期數字
                import re
                m = re.search(r'(\d{1,2})', header)
                if not m:
                    continue
                day_num = int(m.group(1))
                
                day_open_times = []
                for slot in day['slots']:
                    title = slot['title']
                    if '~' not in title:
                        continue
                    try:
                        start_part = title.split('~')[0].strip()
                        end_part = title.split('~')[1].strip()
                        start_h = int(start_part.split(':')[0])
                        # 篩選 14:00-19:00 起始
                        if 14 <= start_h <= 19:
                            day_open_times.append({
                                'start_time': start_part,
                                'end_time': end_part
                            })
                    except:
                        pass
                
                if day_open_times:
                    times_str = ', '.join([f"{s['start_time']}-{s['end_time']}" for s in day_open_times])
                    log(f"  {day_num} 日: {len(day_open_times)} 格 ({times_str})")
                else:
                    # 印出該日所有院外人士時段（不限 14:00-20:00），方便診斷
                    all_times = [slot['title'] for slot in day['slots'] if '~' in slot['title']]
                    if all_times:
                        log(f"  {day_num} 日: 院外人士共有 {len(all_times)} 格（但都不在 14:00-20:00 範圍）")
                        log(f"    全部: {', '.join(all_times[:10])}")
                
                # 檢查是否為目標日期
                if str(day_num) == target_date.split('/')[1]:
                    all_target_slots = day_open_times
            
            log("")
            if all_target_slots:
                log(f"🎯 目標 {target_date} 有 {len(all_target_slots)} 個 14:00-20:00 開放時段")
                for s in all_target_slots:
                    log(f"   ✅ {s['start_time']}-{s['end_time']}")
                
                booking_request = {
                    'date': target_date,
                    'slots': all_target_slots,
                    'timestamp': datetime.now(TAIPEI_TZ).isoformat(),
                    'from_monitor': True
                }
                with open(ALERT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(booking_request, f, ensure_ascii=False, indent=2)
                log(f"✅ Alert 已寫入：{ALERT_FILE}")
            else:
                target_day = target_date.split('/')[1]
                log(f"⚠️ 目標 {target_date} (日={target_day}) 無 14:00-20:00 院外開放時段")
                log("💡 提示：查看上面列出的其他日期，可能有其他可預約時段")
                if os.path.exists(ALERT_FILE):
                    os.remove(ALERT_FILE)
                    log(f"🗑️ 已移除舊 alert 檔案")
            
        except Exception as e:
            log(f"❌ 錯誤: {e}")
            import traceback
            log(traceback.format_exc())
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())