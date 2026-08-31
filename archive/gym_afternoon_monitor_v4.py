#!/usr/bin/env python3
"""
新版 Monitor v4：修正 DOM 結構解析
- 日期：.calendar__day-text（不是 .calendar__day-header）
- 時段：div.timeline__identity（不是 li）
- 院外人士：class 含 non-sinica
- 用 evaluate() 一次抓全部，避免超時
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
    target_day = int(target_date.split('/')[1])
    log(f"📅 目標日期: {target_date} (院外人士 +5 天, 日={target_day})")
    
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
            
            log("批次讀取 DOM...")
            data = await page.evaluate("""
                () => {
                    const days = document.querySelectorAll('.calendar__day-item');
                    const result = [];
                    days.forEach(day => {
                        const dayText = day.querySelector('.calendar__day-text');
                        const dayNum = dayText ? dayText.innerText.trim() : '';
                        const slots = [];
                        day.querySelectorAll('div.timeline__identity').forEach(item => {
                            const cls = item.className;
                            const title = item.getAttribute('title') || '';
                            slots.push({ title, cls });
                        });
                        result.push({ dayNum, slots });
                    });
                    return result;
                }
            """)
            
            log(f"找到 {len(data)} 個日期區塊")
            
            all_target_slots = []
            all_non_sinica_slots = []  # 所有院外人士時段（不限目標日期）
            
            for day in data:
                day_num_str = day['dayNum']
                try:
                    day_num = int(day_num_str)
                except:
                    continue
                
                for slot in day['slots']:
                    title = slot['title']
                    cls = slot['cls']
                    if '~' not in title:
                        continue
                    
                    try:
                        start_part = title.split('~')[0].strip()
                        end_part = title.split('~')[1].strip()
                        start_h = int(start_part.split(':')[0])
                    except:
                        continue
                    
                    is_non_sinica = 'non-sinica' in cls
                    
                    if is_non_sinica and 14 <= start_h <= 19:
                        entry = {
                            'day': day_num,
                            'start_time': start_part,
                            'end_time': end_part
                        }
                        all_non_sinica_slots.append(entry)
                        
                        if day_num == target_day:
                            all_target_slots.append(entry)
            
            # 列出所有院外人士 14:00-20:00 時段
            if all_non_sinica_slots:
                log(f"\n🎾 所有院外人士 14:00-20:00 時段（共 {len(all_non_sinica_slots)} 格）：")
                by_day = {}
                for s in all_non_sinica_slots:
                    by_day.setdefault(s['day'], []).append(s)
                for day in sorted(by_day.keys()):
                    times = [f"{s['start_time']}-{s['end_time']}" for s in by_day[day]]
                    marker = " 👈 目標" if day == target_day else ""
                    log(f"  {day} 日: {', '.join(times)}{marker}")
            else:
                log("⚠️ 完全沒有院外人士 14:00-20:00 時段")
            
            log("")
            if all_target_slots:
                log(f"🎯 目標 {target_date} 有 {len(all_target_slots)} 個開放時段：")
                for s in all_target_slots:
                    log(f"   ✅ {s['start_time']}-{s['end_time']}")
                
                booking_request = {
                    'date': target_date,
                    'slots': [{'start_time': s['start_time'], 'end_time': s['end_time']} for s in all_target_slots],
                    'timestamp': datetime.now(TAIPEI_TZ).isoformat(),
                    'from_monitor': True
                }
                with open(ALERT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(booking_request, f, ensure_ascii=False, indent=2)
                log(f"✅ Alert 已寫入：{ALERT_FILE}")
            else:
                log(f"⚠️ 目標 {target_date} (日={target_day}) 無院外人士 14:00-20:00 時段")
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