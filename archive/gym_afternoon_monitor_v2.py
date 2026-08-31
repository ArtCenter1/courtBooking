#!/usr/bin/env python3
"""
新版 Monitor：使用 Playwright 真實讀取 DOM，找出 14:00-20:00 的院外人士可預約時段
- 不再依賴 title 中的「開放」字樣
- 從 .calendar__day-item 的標題找出日期
- 從 class 找出是否為 non-sinica（院外人士）
- 寫入 ~/.gym_reservation_alert.json
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
    """院外人士：今天 + 5 天"""
    now = datetime.now(TAIPEI_TZ)
    return (now + timedelta(days=5)).strftime('%m/%d')

async def scan_slots(headless=True):
    """使用 Playwright 讀取真實 DOM"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-TW',
            storage_state=r"C:\Users\artce\scripts\state.json"
        )
        page = await context.new_page()
        
        slots = []
        try:
            log("進入預約頁面...")
            await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            
            # 點選「網球場」讓當月完整日曆顯示
            log("選擇網球場...")
            await page.locator('label:has-text("網球場 / Tennis court")').click()
            await page.locator('li[data-label="網球場 / Tennis court"]').click()
            await page.wait_for_timeout(2000)
            
            log("掃描所有日期區塊...")
            # 每個 .calendar__day-item 代表一天
            day_items = await page.locator('.calendar__day-item').all()
            log(f"找到 {len(day_items)} 個日期區塊")
            
            for day in day_items:
                # 從日期標題解析日期
                try:
                    day_header = await day.locator('.calendar__day-header').first.inner_text()
                except:
                    continue
                
                # 從 "26\n週三" 這種格式解析
                # 或 "August 26" 等
                day_num = None
                import re
                m = re.search(r'(\d{1,2})', day_header)
                if m:
                    day_num = int(m.group(1))
                
                if not day_num:
                    continue
                
                # 組合 MM/DD 格式（月份需根據日曆標題判斷，這裡簡化為當月）
                # 實際上日曆會顯示 8月 或 9月，需從外部 .calendar__month-title 讀取
                # 暫時用 target_date 比對
                
                # 找出該日所有院外人士可預約時段
                items = await day.locator('.timeline__identity_non-sinica').all()
                for item in items:
                    title = await item.get_attribute('title')
                    if not title or '~' not in title:
                        continue
                    try:
                        start_part = title.split('~')[0].strip()
                        end_part = title.split('~')[1].strip()
                        start_h = int(start_part.split(':')[0])
                        # 篩選 14:00-19:00 起始（結束最晚 20:00）
                        if 14 <= start_h <= 19:
                            slots.append({
                                'day_num': day_num,
                                'start_time': start_part,
                                'end_time': end_part,
                                'day_header': day_header.strip().replace('\n', ' ')
                            })
                    except Exception as e:
                        pass
            
            await browser.close()
            return slots
        except Exception as e:
            log(f"❌ 掃描失敗: {e}")
            await browser.close()
            return slots

async def main():
    target_date = get_target_date()
    log(f"📅 目標日期: {target_date} (院外人士 +5 天)")
    log("🚀 啟動 Playwright 真實掃描...")
    
    slots = await scan_slots(headless=True)
    
    # 過濾符合目標日期的時段
    # 因為月份可能跨月（8月→9月），這裡用 day_num + 當前月份判斷
    now = datetime.now(TAIPEI_TZ)
    target_day = int(target_date.split('/')[1])
    target_month = int(target_date.split('/')[0])
    
    # 找當月最後一天的 day_num，超過的就是下個月
    # 簡化：假設目標日期若是 09/01，day_num=1 對應 9月
    # 若目標是 08/30，day_num=30 對應 8月
    # 但若日曆同月顯示，day_num=1 可能對應下個月
    
    # 更安全做法：取所有院外人士時段，列出每個 day_num 的時段，讓用戶知道所有可用日期
    log(f"📊 掃描到 {len(slots)} 個院外人士可預約時段（14:00-19:00 起始）")
    
    # 按 day_num 分組
    by_day = {}
    for s in slots:
        by_day.setdefault(s['day_num'], []).append(s)
    
    log("\n所有院外人士 14:00-20:00 開放時段（按日期分組）：")
    for day in sorted(by_day.keys()):
        day_slots = by_day[day]
        times = [f"{s['start_time']}-{s['end_time']}" for s in day_slots]
        log(f"  {day} 日: {len(day_slots)} 格 ({', '.join(times)})")
    
    # 過濾出目標日期的時段
    target_slots = [s for s in slots if s['day_num'] == target_day]
    
    if target_slots:
        log(f"\n🎯 目標日期 {target_date} 共 {len(target_slots)} 個開放時段")
        for s in target_slots:
            log(f"   ✅ {s['start_time']}-{s['end_time']}")
        
        booking_request = {
            'date': target_date,
            'slots': [{'start_time': s['start_time'], 'end_time': s['end_time']} for s in target_slots],
            'timestamp': datetime.now(TAIPEI_TZ).isoformat(),
            'from_monitor': True
        }
        with open(ALERT_FILE, 'w', encoding='utf-8') as f:
            json.dump(booking_request, f, ensure_ascii=False, indent=2)
        log(f"✅ 已寫入預約請求：{ALERT_FILE}")
    else:
        log(f"\n⚠️ 目標日期 {target_date} 無院外人士 14:00-20:00 開放時段")
        log("💡 提示：查看上面「所有院外人士時段」可能是其他日期")
        if os.path.exists(ALERT_FILE):
            os.remove(ALERT_FILE)
            log(f"🗑️ 已移除舊的 alert 檔案")

if __name__ == "__main__":
    asyncio.run(main())