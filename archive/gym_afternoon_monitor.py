#!/usr/bin/env python3
"""
中研院體育館網球場預約監控 - 一次性檢查可預約時段並寫入預約請求文件
設計為透過 cron 每日固定時間執行 (例如 14:00)
偵測 HTML 中預先渲染的即將開放時段（下午/晚上 14:00-20:00）
若發現時段，寫入 ~/.gym_reservation_alert.json 供預約腳本使用
若未發現時段，不寫入檔案（預約腳本將改為 fallback 掃描 14:00-20:00）
"""
import urllib.request
import ssl
import re
import os
from datetime import datetime, timedelta, timezone
import json

URL = "https://gym.dga.sinica.edu.tw/reservation.html"
ALERT_FILE = os.path.expanduser("~/.gym_reservation_alert.json")
LOG_FILE = os.path.expanduser("~/.gym_monitor.log")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

TAIPEI_TZ = timezone(timedelta(hours=8))

def get_target_date():
    """取得目標日期：今天 + 5 天（院外人士規則）"""
    now = datetime.now(TAIPEI_TZ)
    target = now + timedelta(days=5)
    return target.strftime('%m/%d')

def log(msg):
    timestamp = datetime.now(TAIPEI_TZ).strftime('%H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def check_available_slots(target_date):
    """檢查系統中有哪些可預約的時段（下午/晚上 14:00-20:00）"""
    try:
        req = urllib.request.Request(URL, headers=HEADERS)
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        html = resp.read().decode('utf-8')

        # 尋找所有標示「開放」的時段
        # 格式: title="HH:MM~HH:MM MM/DD開放"
        pattern = r'title="(\d{2}:\d{2})~(\d{2}:\d{2})\s+(\d{2}/\d{2})開放"'
        matches = re.findall(pattern, html)

        # 篩選下午/晚上時段（14:00-19:00 起始，結束最晚 20:00）
        # 並過濾目標日期
        available_slots = []
        for start, end, date in matches:
            if date != target_date:
                continue
            start_hour = int(start.split(':')[0])
            if 14 <= start_hour <= 19:  # 14:00-19:00 起始的時段 (結束時間最晚 20:00)
                available_slots.append({
                    'date': date,
                    'start_time': start,
                    'end_time': end,
                })

        # 按開始時間排序
        available_slots.sort(key=lambda x: x['start_time'])
        return available_slots

    except Exception as e:
        log(f"❌ 檢查失敗: {e}")
        return []

def main():
    target_date = get_target_date()
    print("=" * 60)
    print("中研院體育館網球場預約監控（一次性檢查模式）")
    print("=" * 60)
    print("")
    log("🔧 開始檢查可用時段...")
    print("")
    print(f"⏳ 檢查系統的可用時段 (下午/晚上 14:00-20:00)")
    print(f"📅 目標日期: {target_date} (+5天 院外人士規則)")
    print(f"🎯 回傳所有可用時段")
    print("")

    slots = check_available_slots(target_date)

    if slots:
        log(f"🎯 發現可預約時段")
        for slot in slots:
            log(f"   ✅ {slot['start_time']}-{slot['end_time']} ({slot['date']})")
        
        # 寫入預約請求文件（新格式：slots 陣列）
        booking_request = {
            'date': target_date,
            'slots': slots,
            'timestamp': datetime.now(TAIPEI_TZ).isoformat(),
            'from_monitor': True
        }
        with open(ALERT_FILE, 'w', encoding='utf-8') as f:
            json.dump(booking_request, f, ensure_ascii=False, indent=2)
        log(f"✅ 已寫入預約請求文件！路徑: {ALERT_FILE}")
        log(f"   日期: {target_date}")
        log(f"   時段數: {len(slots)}")
        for slot in slots:
            log(f"   - {slot['start_time']}-{slot['end_time']}")
        log("")
        log("📐 預約腳本將在 00:00 讀取此檔案並預約最早連續 ≤2小時時段")
    else:
        log(f"✅ 目前 {target_date} 無下午/晚上可預約時段 (14:00-20:00)")
        # 移除舊的 alert 檔案（如果存在），以 signal 需要走 fallback
        if os.path.exists(ALERT_FILE):
            os.remove(ALERT_FILE)
            log(f"🗑️ 已移除舊的預約請求文件：{ALERT_FILE}")
        log("")
        log("📐 預約腳本將在 00:00 執行 fallback：掃描 14:00-20:00 找最早連續 ≤2小時")

if __name__ == "__main__":
    main()