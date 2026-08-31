#!/usr/bin/env python3
"""
新版 Monitor v5：周末优先 + 连续时段优先
规则：
1. 周末（周六、周日）14:00-20:00 时段为第一优先
2. 能连续订场（2个连续1小时）的时段优先
3. 扫描所有可见日期，按优先级排序
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

def is_weekend(day_num, month=8):
    """判断某日是周末（周六或周日）"""
    try:
        date = datetime(2026, month, day_num)
        return date.weekday() in (5, 6)  # 5=周六, 6=周日
    except:
        return False

def find_consecutive_slots(slots, max_hours=2):
    """从时段列表中找出最早的连续时段链"""
    if not slots:
        return []
    slots = sorted(slots, key=lambda x: x['start_time'])
    best_chain = []
    current_chain = []
    for slot in slots:
        start = slot['start_time']
        end = slot['end_time']
        if not current_chain:
            current_chain = [slot]
        else:
            last_end = current_chain[-1]['end_time']
            if last_end == start and len(current_chain) < max_hours:
                current_chain.append(slot)
            else:
                if len(current_chain) > len(best_chain):
                    best_chain = current_chain[:]
                current_chain = [slot]
    if len(current_chain) > len(best_chain):
        best_chain = current_chain
    return best_chain

async def scan_all_slots():
    """扫描所有日期的院外人士时段"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-TW',
            storage_state=r"C:\Users\artce\scripts\state.json"
        )
        page = await context.new_page()
        
        try:
            await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
            await page.wait_for_load_state("networkidle")
            
            await page.locator('label:has-text("網球場 / Tennis court")').click()
            await page.locator('li[data-label="網球場 / Tennis court"]').click()
            await page.wait_for_timeout(3000)
            
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
            
            await browser.close()
            return data
        except Exception as e:
            log(f"扫描失败: {e}")
            await browser.close()
            return []

async def main():
    log("🚀 启动 Playwright 扫描所有日期...")
    data = await scan_all_slots()
    log(f"找到 {len(data)} 个日期区块")
    
    # 解析所有院外人士 14:00-20:00 时段
    all_slots = {}  # day_num -> list of slots
    
    for day in data:
        day_num_str = day['dayNum']
        try:
            day_num = int(day_num_str)
        except:
            continue
        
        day_slots = []
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
            
            if 'non-sinica' in cls and 14 <= start_h <= 19:
                day_slots.append({
                    'start_time': start_part,
                    'end_time': end_part
                })
        
        if day_slots:
            all_slots[day_num] = day_slots
    
    # 分类：周末 vs 平日
    weekend_slots = {}  # 周末
    weekday_slots = {}  # 平日
    
    for day_num, slots in all_slots.items():
        if is_weekend(day_num):
            weekend_slots[day_num] = slots
        else:
            weekday_slots[day_num] = slots
    
    # 打印所有时段
    log("\n📊 所有院外人士 14:00-20:00 时段：")
    
    if weekend_slots:
        log(f"\n🌟 周末时段（优先）：")
        for day in sorted(weekend_slots.keys()):
            slots = weekend_slots[day]
            times = [f"{s['start_time']}-{s['end_time']}" for s in slots]
            consecutive = find_consecutive_slots(slots)
            consecutive_str = ""
            if len(consecutive) >= 2:
                consecutive_str = f" 👈 可连续订 {len(consecutive)}h ({consecutive[0]['start_time']}-{consecutive[-1]['end_time']})"
            log(f"  {day} 日: {', '.join(times)}{consecutive_str}")
    
    if weekday_slots:
        log(f"\n📅 平日时段：")
        for day in sorted(weekday_slots.keys()):
            slots = weekday_slots[day]
            times = [f"{s['start_time']}-{s['end_time']}" for s in slots]
            consecutive = find_consecutive_slots(slots)
            consecutive_str = ""
            if len(consecutive) >= 2:
                consecutive_str = f" 👈 可连续订 {len(consecutive)}h ({consecutive[0]['start_time']}-{consecutive[-1]['end_time']})"
            log(f"  {day} 日: {', '.join(times)}{consecutive_str}")
    
    # 按优先级选择最佳时段
    # 优先级 1：周末 + 连续
    # 优先级 2：平日 + 连续
    # 优先级 3：周末 + 不连续
    # 优先级 4：平日 + 不连续
    
    best_slots = []
    best_source = ""
    
    # 找周末连续
    for day in sorted(weekend_slots.keys()):
        consecutive = find_consecutive_slots(weekend_slots[day])
        if len(consecutive) >= 2:
            best_slots = consecutive
            best_source = f"周末 {day} 日连续 {len(consecutive)}h"
            break
    
    # 找平日连续
    if not best_slots:
        for day in sorted(weekday_slots.keys()):
            consecutive = find_consecutive_slots(weekday_slots[day])
            if len(consecutive) >= 2:
                best_slots = consecutive
                best_source = f"平日 {day} 日连续 {len(consecutive)}h"
                break
    
    # 找周末任意
    if not best_slots:
        for day in sorted(weekend_slots.keys()):
            if weekend_slots[day]:
                best_slots = [weekend_slots[day][0]]
                best_source = f"周末 {day} 日单小时"
                break
    
    # 找平日任意
    if not best_slots:
        for day in sorted(weekday_slots.keys()):
            if weekday_slots[day]:
                best_slots = [weekday_slots[day][0]]
                best_source = f"平日 {day} 日单小时"
                break
    
    log("")
    if best_slots:
        # 确定日期
        if best_slots:
            # 从 best_source 解析日期
            target_day = int(best_source.split()[1])
            target_date = f"08/{target_day:02d}"  # 假设8月
            
            log(f"🎯 最佳时段（{best_source}）：")
            for s in best_slots:
                log(f"   ✅ {s['start_time']}-{s['end_time']}")
            
            booking_request = {
                'date': target_date,
                'slots': [{'start_time': s['start_time'], 'end_time': s['end_time']} for s in best_slots],
                'timestamp': datetime.now(TAIPEI_TZ).isoformat(),
                'from_monitor': True,
                'priority': best_source
            }
            with open(ALERT_FILE, 'w', encoding='utf-8') as f:
                json.dump(booking_request, f, ensure_ascii=False, indent=2)
            log(f"✅ Alert 已写入：{ALERT_FILE}")
        else:
            log("⚠️ 无最佳时段")
            if os.path.exists(ALERT_FILE):
                os.remove(ALERT_FILE)
    else:
        log("⚠️ 完全无院外人士 14:00-20:00 时段")
        if os.path.exists(ALERT_FILE):
            os.remove(ALERT_FILE)

if __name__ == "__main__":
    asyncio.run(main())