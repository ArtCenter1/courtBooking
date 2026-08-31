#!/usr/bin/env python3
"""
中研院體育館網球場預約提醒腳本
於 23:58 執行，提醒使用者票券將於 00:00 放出
"""
import urllib.request
import ssl
import json
import os
from datetime import datetime, timedelta, timezone

# Telegram Bot 設定（從現有腳本中取得）
BOT_TOKEN = "440301560:AAEymfQYKqVYqfwtf4fasdfasdfasdfasdfasdf"  # 需要替換為真實 token
CHAT_ID = "440301560"  # 從之前的 logs 中看到

# 如果沒有真實 token，則只寫入 log 檔案
USE_TELEGRAM = False  # 設為 True 時需要填入真實的 BOT_TOKEN

LOG_FILE = os.path.expanduser("~/.gym_reminder.log")

def log(msg):
    timestamp = datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def send_telegram_message(message):
    if not USE_TELEGRAM:
        log(f"📱 [模擬] Telegram 訊息: {message}")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    data_encoded = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=data_encoded, headers={'Content-Type': 'application/json'})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            result = response.read().decode('utf-8')
            log(f"✅ Telegram 訊息已發送: {message[:50]}...")
    except Exception as e:
        log(f"❌ Telegram 訊息發送失敗: {e}")

def main():
    print("=" * 50)
    print("中研院體育館網球場預約提醒")
    print("=" * 50)
    
    message = "🔔 中研院體育館網球場票券將於 00:00 放出，請準備進行自動預約。"
    
    log("🕛 發送 00:00 放票前 2 分鐘提醒")
    send_telegram_message(message)
    
    print("✅ 提醒已發送")

if __name__ == "__main__":
    main()