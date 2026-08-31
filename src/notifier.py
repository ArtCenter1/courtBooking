"""
通知與日誌模組 (Notifier & Logger)
支援本地檔案日誌寫入、控制台彩色輸出及 Telegram 即時通知。
"""

import os
import json
import urllib.request
import ssl
from datetime import datetime
from src.time_sync import get_now, TAIPEI_TZ

class Notifier:
    def __init__(self, log_file=r"C:\Users\artce\scripts\booking.log", tg_config=None):
        self.log_file = log_file
        self.tg_config = tg_config or {}
        # 確保 log 目錄存在
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    def log(self, msg: str, to_console=True, to_file=True):
        timestamp = get_now().strftime('%H:%M:%S.%f')[:-3]
        line = f"[{timestamp}] {msg}"
        if to_console:
            print(line, flush=True)
        if to_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
            except Exception as e:
                print(f"寫入日誌檔案失敗: {e}")

    def send_telegram(self, message: str):
        if not self.tg_config.get('enabled', False):
            return False
        bot_token = self.tg_config.get('bot_token')
        chat_id = self.tg_config.get('chat_id')
        if not bot_token or not chat_id:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            data_encoded = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, headers={'Content-Type': 'application/json'})
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                return True
        except Exception as e:
            self.log(f"⚠️ Telegram 發送失敗: {e}")
            return False
