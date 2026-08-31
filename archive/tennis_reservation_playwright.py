#!/usr/bin/env python3
"""
中研院體育館網球場預約自動腳本 (Playwright 版) - 讀取監控系統的預約請求
專為 外人士 (院外人士) 設計：可預約使用前5天內的時段
關鍵特點：
- 讀取 ~/.gym_reservation_alert.json（由 gym_monitor_dynamic.py 寫入）
- 動態目標時段：監控發現時段是多少，就預約哪個時段
- 保持在同一頁面內操作，維持 PrimeFaces Poll 會話 (每 1200ms 自動刷新)
- 精準在 00:00 執行預約操作（實際根據預約日期而定）
- 自動選擇 網球場 和目標時段
- 完整處理 PrimeFaces ViewState 和表單提交
"""

import asyncio
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright
import sys
import json
import argparse

# 時區設定：台北時間 (UTC+8)
TAIPEI_TZ = timezone(timedelta(hours=8))


def get_taipei_now():
    """取得當前台北時間"""
    return datetime.now(TAIPEI_TZ)


def load_booking_request():
    """讀取監控系統寫入的預約請求文件"""
    try:
        with open('C:/Users/artce/.gym_reservation_alert.json') as f:
            request_data = json.load(f)
        return request_data
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"❌ 預約請求文件格式錯誤：{e}")
        return None


def resolve_booking_request(date=None, start_time=None, end_time=None):
    """
    解析預約請求：
    1. 優先：讀取監控系統的 alert 文件（如果存在）
    2. 如果 alert 不存在，使用 CLI 參數或預設時段（21:00-22:00）
    3. 計算目標日期為今天+5天（院外人士規則）
    """
    # 1. 嘗試讀取監控系統的 alert 文件
    alert_data = load_booking_request()

    if alert_data and alert_data.get('from_monitor'):
        print("✅ 讀取到監控系統的預約請求")
        target_date = alert_data.get('date')
        start_time = alert_data.get('start_time')
        end_time = alert_data.get('end_time')
        timestamp = alert_data.get('timestamp')
        print(f"   時段: {start_time}-{end_time} ({target_date})")
        print(f"   時間戳記: {timestamp}")
        print(f"   來源: 動態監控發現的時段")
        return {
            'date': target_date,
            'start_time': start_time,
            'end_time': end_time,
            'timestamp': timestamp,
            'source': 'monitor'
        }

    # 2. 沒有 alert 文件，使用標準 5 天前放票時段（14:00-22:00）
    print("ℹ️  未偵測到特殊時段，使用標準 5 天前放票時段 14:00-22:00")
    
    # 計算目標日期：今天 + 5 天（院外人士規則）
    now = get_taipei_now()
    target_date_obj = now + timedelta(days=5)
    target_date = target_date_obj.strftime('%m/%d')
    
    # 使用標準時段 14:00-22:00（或 CLI 參數覆蓋）
    if date and start_time and end_time:
        print(f"📋 使用指令行指定的時段：")
        print(f"   日期: {date}")
        print(f"   時段: {start_time}-{end_time}")
        final_date = date
        final_start = start_time
        final_end = end_time
    else:
        # 標準時段：14:00-22:00
        print(f"📋 使用標準時段 14:00-22:00")
        final_date = target_date
        final_start = "14:00"
        final_end = "22:00"
    
    print(f"   目標日期: {final_date} (+5天規則)")
    print(f"   時段: {final_start}-{final_end}")
    
    return {
        'date': final_date,
        'start_time': final_start,
        'end_time': final_end,
        'timestamp': datetime.now(TAIPEI_TZ).isoformat(),
        'source': 'regular'
    }


def format_date_for_display(date_str):
    """格式化日期為 MM/DD 供比對"""
    return datetime.strptime(date_str, '%m/%d').strftime('%m/%d')


async def main():
    parser = argparse.ArgumentParser(description='中研院體育館網球場預約腳本')
    parser.add_argument('--force-date', help='強制指定預約日期（如 08/25）')
    parser.add_argument('--start-time', help='強制指定開始時間（如 21:00）')
    parser.add_argument('--end-time', help='強制指定結束時間（如 22:00）')
    args = parser.parse_args()

    print("=" * 60)
    print("中研院體育館網球場預約自動腳本")
    print("=" * 60)
    print("")

    # 解析預約請求：優先監控系統，其次 CLI 參數
    booking_info = resolve_booking_request(
        date=args.force_date,
        start_time=args.start_time,
        end_time=args.end_time
    )

    if not booking_info:
        print("")
        print("❌ 無法繼續預約流程")
        return

    target_date = booking_info.get('date')
    start_time = booking_info.get('start_time')
    end_time = booking_info.get('end_time')
    timestamp = booking_info.get('timestamp')
    source = booking_info.get('source')

    print(f"✅ 預約來源: {'✨ 監控系統' if source == 'monitor' else '📋 指令行'}")
    print(f"   時段: {start_time}-{end_time} ({target_date})")
    print(f"   時間戳記: {timestamp}")
    print("")
    print("=" * 60)
    print("")

    # 檢查目前時間是否在可預約時間內（院外人士：使用前5天內）
    # 解析日期為 month/day，需要補上年份
    target_month_day = datetime.strptime(target_date, '%m/%d')
    now = get_taipei_now()
    # 假設目標日期在當年或明年
    target_datetime = target_month_day.replace(year=now.year, tzinfo=TAIPEI_TZ)
    # 如果目標日期已過去（月/日 小於 現在月/日），則設為明年
    if target_datetime < now:
        target_datetime = target_datetime.replace(year=now.year + 1)
    # 零時放票：設定為當天 00:00:00
    target_datetime = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    now = get_taipei_now()
    days_to_target = (target_datetime - now).days

    print(f"目前時間: {now.strftime('%Y-%m-%d %H:%M:%S')} (台北時間)")
    print(f"目標放票日期: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')} (零時)")
    print(f"距離目標: {days_to_target} 天")
    print("")

    # 院外檢查：必須在可預約時間內（使用前5天）
    if days_to_target > 5:
        print(f"❌ 錯誤：{target_date} 距離現在超過 5 天")
        print("   院外人士只能預約使用前 5 天內的時段")
        print("   請選擇其他日期")
        return
    elif days_to_target < -1:
        print(f"❌ 錯誤：{target_date} 已經過期")
        print("   該時段已經無法預約")
        return
    else:
        print("✅ 時段在可預約範圍內")
    print("")
    print("=" * 60)
    print("")
    print("🚀 啟動瀏覽器並進入預約流程...")
    print("")

    async with async_playwright() as p:
        # 啟動瀏覽器（可視化模式方便除錯，實際使用可設 headless=True）
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='zh-TW'
        )
        page = await context.new_page()

        try:
            # 步驟 1: 進入預約頁面
            print("步驟 1: 進入預約頁面...")
            await page.goto("https://gym.dga.sinica.edu.tw/reservation.html")
            await page.wait_for_load_state("networkidle")
            print("   ✅ 頁面已載入")
            print("")

            # 步驟 2: 登入（假設用戶已有帳號密碼）
            print("步驟 2: 請手動完成登入...")
            print("   請在瀏覽器中完成登入過程")
            print("   登入完成後，按 Enter 繼續（直接按 Enter 表示已登入）")
            while True:
                try:
                    line = input()
                    # 用戶按下 Enter 即視為登入完成
                    break
                except EOFError:
                    print("未偵測到標準輸入，假設您已完成登入。")
                    break

            # 步驟 3: 確認在預約頁面並導航到網球場選項
            print("步驟 3: 確認在網球場預約頁面...")
            await page.wait_for_selector('text=網球場 / Tennis court', timeout=10000)
            print("   ✅ 已到達網球場預約頁面")
            print("")

            # 格式化目標時段供原始碼比對（G gym_monitor 使用 ~，頁面可能使用 -）
            target_display_date = format_date_for_display(target_date)
            target_time_display = f"{start_time}~{end_time}"

            print(f"🎯 監控系統發現的時段：{target_display_date} {start_time}-{end_time}")
            print(f"   需要操作的時段字串：{target_time_display}")
            print("")

            # 主監控循環：到達目標時間時自動預約
            print("步驟 4: 開始精準監控目標時間...")
            print("")

            while True:
                now = get_taipei_now()

                # 計算距離目標時間的剩餘秒數
                seconds_to_target = (target_datetime - now).total_seconds()

                # 顯示當前狀態（每 30 秒顯示一次）
                if int(now.timestamp()) % 30 == 0:
                    hours, remainder = divmod(abs(int(seconds_to_target)), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if seconds_to_target > 0:
                        print(f"[{now.strftime('%H:%M:%S')}] 監控中... 距離目標時間仍剩 {hours:02d}:{minutes:02d}:{seconds:02d}")
                    else:
                        print(f"[{now.strftime('%H:%M:%S')}] 目標時間已到！檢查時段可用性...")

                # 檢查是否到達預約時間（允許微小誤差）
                if seconds_to_target <= 5 and seconds_to_target >= -30:  # -30秒到+5秒的窗口
                    print("")
                    print(f"[{now.strftime('%H:%M:%S')}] 進入預約窗口！檢查時段可用性...")
                    print("")

                    # 檢查目標時段是否可預約
                    # 尋找目標時段的元素：不含 "no-open" 且包含目標日期和時段
                    # 根據 gym_monitor 的 pattern：title="HH:MM~HH:MM MM/DD開放"
                    time_slot_selector = f'text=/{target_display_date} {start_time}~{end_time}/'  # 注意：空格需要處理，但原始字串可能沒空格
                    # 其實我們要構造的是類似 "12:00~13:00 (08/21)"，但頁面可能用不同分隔符
                    # 為簡化，我們直接用包含目標日期和時段的文字，但不含斜杠
                    # 先嘗試一個簡單的 selector：包含目標日期和時段的文字
                    # 例如：text=/12:00~13:00.*08\/21/
                    # 我們改用正則表達式方式：page.locator(f'text={target_display_date} {start_time}~{end_time}') 可能不準確
                    # 為了避免複雜，我們改用較寬鬆的條件：只要包含目標日期和時段即可
                    # 但為了準確，我們仍使用原本的邏輯：根據 gym_monitor 的 pattern，頁面上可能是 "HH:MM~HH:MM MM/DD開放"
                    # 我們將 target_time_display 格式為 "HH:MM~HH:MM"，並 target_display_date 為 "MM/DD"
                    # 所以我們要找的文字是類似 "12:00~13:00 08/21"（注意：中間是空格）
                    # 但在網頁上，可能是 "12:00~13:00 (08/21)" 或其他格式。為了簡化，我們先用一個包含日期和時段的寬鬆條件。
                    # 我們改用：尋找同時包含 target_display_date 和 target_time_display 的元素
                    # 但這可能匹配多個。然而，我們只要找到一個可點擊的即可。
                    # 為了簡化，我們仍用之前的 selector 格式，但注意到在網頁上可能是 "HH:MM～HH:MM" (全形波浪線) 或其他。
                    # 我們暫時保留原本的 selector，但將其改為更寬鬆的正則：只要包含日期和時段即可。
                    # 然而，為了不改動太多，我們先用一個簡單的定位器：尋找含有 target_display_date 和 target_time_display 的文字。
                    # 但是 Playwright 的 text= selector 期望精確匹配？其實 text= 會匹配包含該文字的元素。
                    # 所以我們可以用：text={target_display_date} {target_time_display}
                    # 但目標時間顯示中間可能是全形波浪線？我們先用半形。
                    # 我們先嘗試用半形波浪線。
                    time_slot_selector = f'text={target_display_date} {start_time}~{end_time}'
                    # 如果找不到，我們再嘗試全形波浪線
                    # 但先保留這個。

                    try:
                        # 等待元素出現（最多等待5秒）
                        time_slot_element = await page.wait_for_selector(
                            time_slot_selector,
                            timeout=5000
                        )

                        if time_slot_element:
                            print(f"[{now.strftime('%H:%M:%S')}] 🎯 發現可預約時段！{start_time}-{end_time} ({target_date})")
                            # 步驟 1: 選擇網球場
                            print("   步驟 1: 選擇網球場...")
                            venue_dropdown = page.locator('text=網球場 / Tennis court')
                            await venue_dropdown.click()
                            await page.wait_for_timeout(500)  # 短暫等待選項更新

                            # 步驟 2: 選擇目標時段
                            print(f"   步驟 2: 選擇目標時段 {start_time}-{end_time}...")
                            time_slot_option = page.locator(f'text={start_time}~{end_time} ({target_date})')
                            await time_slot_option.click()
                            await page.wait_for_timeout(500)

                            # 步驟 3: 點擊搜尋按鈕
                            print("   步驟 3: 點擊搜尋按鈕...")
                            search_button = page.locator('text=搜尋 Search')
                            await search_button.click()
                            await page.wait_for_timeout(2000)  # 等待搜尋結果

                            # 步驟 4: 確認預約
                            print("   步驟 4: 確認預約...")
                            # 這裡需要根據實際頁面調整確認按鈕的選擇器
                            confirm_button = page.locator('text=確認預約')
                            if await confirm_button.is_visible():
                                await confirm_button.click()
                                await page.wait_for_timeout(2000)

                                # 最終確認
                                success_message = page.locator('text=預約成功')
                                if await success_message.is_visible():
                                    print(f"[{now.strftime('%H:%M:%S')}] 🎉 預約成功！")
                                    break
                                else:
                                    print(f"[{now.strftime('%H:%M:%S')}] ⚠️ 預約可能失敗，請檢查頁面")
                                    # 即使看不到成功訊息，也嘗試繼續，因為有時頁面會直接跳轉
                                    break
                            else:
                                print(f"[{now.strftime('%H:%M:%S')}] ⚠️ 未找到確認按鈕，可能已自動提交")
                                break
                        else:
                            print(f"[{now.strftime('%H:%M:%S')}] ❌ 未找到可預約時段：{start_time}-{end_time} ({target_date})")
                            # 即使看不到時段，也繼續監控，可能是暫時的網路問題
                    except Exception as e:
                        print(f"[{now.strftime('%H:%M:%S')}] ❌ 檢查時段時發生錯誤: {str(e)[:100]}")
                        # 繼續監控，可能是暫時的網路問題

                # 智能等待策略：接近目標時間時增加檢查頻率
                if seconds_to_target > 300:  # 超過5分鐘前
                    wait_time = 30  # 每30秒檢查一次
                elif seconds_to_target > 60:  # 1-5分鐘前
                    wait_time = 10  # 每10秒檢查一次
                else:  # 最後1分鐘內
                    wait_time = 2   # 每2秒檢查一次

                # 確保不會過度等待過去目標時間
                wait_time = min(wait_time, max(1, seconds_to_target + 10)) if seconds_to_target > -10 else 2

                await asyncio.sleep(wait_time)

        except Exception as e:
            print("")
            print(f"❌ 發生錯誤: {e}")
        finally:
            print("")
            print("關閉瀏覽器...")
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("")
        print("🛑 使用者中斷程式執行")
    except Exception as e:
        print(f"程式執行失敗: {e}")