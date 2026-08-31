# tennis_reservation_playwright_state.py - 防弹版 v2.3 (立即B计划)
import asyncio
import argparse
import os
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

TAIPEI_TZ = timezone(timedelta(hours=8))
LOG_FILE = r"C:\Users\artce\scripts\booking.log"

def log(msg):
    timestamp = datetime.now(TAIPEI_TZ).strftime('%H:%M:%S.%f')[:-3]
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_taipei_now():
    return datetime.now(TAIPEI_TZ)

async def try_click_slot(page, slot_title, timeout=2000):
    """尝试点击时段并确认，返回 True/False"""
    try:
        slot = page.locator(f'.timeline__identity[title*="{slot_title}"]')
        if await slot.count() == 0:
            return False
        await slot.first.click()
        confirm_btn = page.locator('button:has-text("確認預約")')
        await confirm_btn.wait_for(state="visible", timeout=timeout)
        await confirm_btn.click()
        await page.wait_for_timeout(500)
        return True
    except:
        return False

async def scan_available_slots(page):
    """扫描当前页面所有院外人士 14:00-20:00 时段"""
    slots = await page.evaluate("""
        () => {
            const result = [];
            document.querySelectorAll('.calendar__day-item').forEach(day => {
                const dayText = day.querySelector('.calendar__day-text');
                const dayNum = dayText ? dayText.innerText.trim() : '';
                day.querySelectorAll('div.timeline__identity_non-sinica').forEach(item => {
                    const title = item.getAttribute('title') || '';
                    if (title.includes('~')) {
                        result.push({ day: dayNum, title: title });
                    }
                });
            });
            return result;
        }
    """)
    return slots

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, help='日期 MM/DD')
    parser.add_argument('--court', choices=['A', 'B'], default='A')
    parser.add_argument('--slots', default='18:00,19:00', help='逗号分隔时段')
    args = parser.parse_args()

    primary_slots = [s.strip() for s in args.slots.split(',')]
    log(f"=== 启动预约任务：{args.date} 网球场 {args.court} ===")
    log(f"🎯 A 计划（第一目标）：{primary_slots}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state=r"C:\Users\artce\scripts\state.json")
        page = await context.new_page()

        try:
            log("正在进入预约页面...")
            await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
            await page.wait_for_load_state("networkidle")
            
            # 预选场地
            log("预选网球场...")
            await page.locator('label:has-text("網球場 / Tennis court")').click()
            await page.locator('li[data-label="網球場 / Tennis court"]').click()
            await page.wait_for_timeout(1000)

            # 收起下拉选单
            log("收起下拉选单...")
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
            await page.locator('body').click(position={"x": 10, "y": 10})
            await page.wait_for_timeout(500)

            # 选择场地 A/B
            log(f"选择网球场 {args.court}...")
            tab_links = page.locator('.r-tab__link')
            if args.court == 'A': 
                await tab_links.first.click(force=True)
            else: 
                await tab_links.nth(1).click(force=True)
            await page.wait_for_timeout(1000)

            # 等待 00:00
            now = get_taipei_now()
            target_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if now.hour >= 12: target_time += timedelta(days=1)
            
            log(f"⏱️ 目标放票时间：{target_time}")
            
            # 倒计时
            while get_taipei_now() < (target_time - timedelta(seconds=2)):
                remaining = (target_time - get_taipei_now()).total_seconds()
                if remaining < 10:
                    print(f"  倒数 {remaining:.1f} 秒...", end='\r')
                await asyncio.sleep(0.2)

            log("🔔 时间到！开始刷新...")
            search_btn = page.locator('text=搜尋 Search')
            
            # 疯狂刷新直到时段出现
            booking_success = False
            
            for attempt in range(30):
                await search_btn.click()
                await page.wait_for_timeout(500)
                
                # 尝试 A 计划
                a_plan_success = False
                for s_time in primary_slots:
                    if await try_click_slot(page, s_time):
                        log(f"✅ A 计划成功：{s_time}")
                        a_plan_success = True
                        break
                
                if a_plan_success:
                    booking_success = True
                    break
                
                # A 计划失败，立即启动 B 计划（不再等待）
                log("⚠️ A 计划失败，启动 B 计划扫描...")
                all_slots = await scan_available_slots(page)
                # 过滤 14:00-20:00 并排序
                b_plan_candidates = []
                for s in all_slots:
                    try:
                        start_h = int(s['title'].split('~')[0].split(':')[0])
                        if 14 <= start_h <= 19:
                            b_plan_candidates.append(s)
                    except:
                        pass
                
                if b_plan_candidates:
                    log(f"📋 B 计划候选：{len(b_plan_candidates)} 个时段")
                    for c in b_plan_candidates[:5]:
                        log(f"   - {c['day']}日 {c['title']}")
                
                # 立即尝试 B 计划候选
                for candidate in b_plan_candidates:
                    if await try_click_slot(page, candidate['title'].split('~')[0]):
                        log(f"✅ B 计划成功：{candidate['day']}日 {candidate['title']}")
                        booking_success = True
                        break
                if booking_success:
                    break
            
            if not booking_success:
                log("❌ A/B 计划均未成功")
            else:
                log("🎉 预约流程完成！")
            
            await page.screenshot(path=r"C:\Users\artce\scripts\final_result.png")
            
        except Exception as e:
            log(f"❌ 严重错误: {e}")
            await page.screenshot(path=r"C:\Users\artce\scripts\error_final.png")
        finally:
            log("任务结束，关闭浏览器。")
            await asyncio.sleep(5)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())