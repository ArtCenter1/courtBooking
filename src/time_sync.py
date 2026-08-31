"""
毫秒級時間同步模組 (Time Synchronization)
支援 SNTP (RFC 4330) 與 HTTP Date Response Header 雙重校準，計算本機與伺服器時間漂移 (Clock Drift)。
"""

import socket
import struct
import time
import urllib.request
import ssl
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

TAIPEI_TZ = timezone(timedelta(hours=8))

class TimeSync:
    def __init__(self, ntp_server="time.stdtime.gov.tw", http_url="https://gym.dga.sinica.edu.tw/reservation.html"):
        self.ntp_server = ntp_server
        self.http_url = http_url
        self.drift_seconds = 0.0  # server_time - local_time

    def sync_via_sntp(self, timeout=3.0):
        """透過 SNTP 協議直接查詢國家標準時間 (毫秒級精度)"""
        # NTP packet format: 48 bytes, mode 3 (client) in first byte: 0x1B
        NTP_PORT = 123
        NTP_DELTA = 2208988800  # 1970-01-01 to 1900-01-01 in seconds
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(timeout)
        try:
            data = b'\x1b' + 47 * b'\0'
            t1 = time.time()
            client.sendto(data, (self.ntp_server, NTP_PORT))
            data, address = client.recvfrom(1024)
            t4 = time.time()
            
            if data:
                # Transmit Timestamp is at offset 40..48
                unpacked = struct.unpack("!12I", data[0:48])
                transmit_seconds = unpacked[10] - NTP_DELTA
                transmit_fraction = unpacked[11] / (2**32)
                t3 = transmit_seconds + transmit_fraction
                
                # RTT and offset
                rtt = t4 - t1
                server_time = t3 + (rtt / 2.0)
                self.drift_seconds = server_time - t4
                return True, self.drift_seconds, "SNTP"
        except Exception as e:
            return False, 0.0, str(e)
        finally:
            client.close()

    def sync_via_http(self, timeout=3.0):
        """透過目標網站 HTTP Date 響應標頭進行備用校準"""
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                self.http_url,
                method='HEAD',
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            t1 = time.time()
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
                t2 = time.time()
                date_str = response.headers.get('Date')
                if date_str:
                    server_dt = parsedate_to_datetime(date_str)
                    server_timestamp = server_dt.timestamp()
                    local_timestamp = (t1 + t2) / 2.0
                    self.drift_seconds = server_timestamp - local_timestamp
                    return True, self.drift_seconds, "HTTP_Date"
        except Exception as e:
            return False, 0.0, str(e)
        return False, 0.0, "No Date header"

    def calibrate(self):
        """校準時鐘，優先使用 SNTP，失敗則回退 HTTP Date"""
        ok, drift, method = self.sync_via_sntp()
        if not ok:
            ok, drift, method = self.sync_via_http()
        if ok:
            self.drift_seconds = drift
            return True, self.drift_seconds, method
        else:
            self.drift_seconds = 0.0
            return False, 0.0, method

    def get_synced_now(self):
        """取得校準後的當前台北時間 (datetime)"""
        now_ts = time.time() + self.drift_seconds
        return datetime.fromtimestamp(now_ts, tz=TAIPEI_TZ)

    def get_synced_timestamp(self):
        """取得校準後的 UTC timestamp (float)"""
        return time.time() + self.drift_seconds

# 全局單例
time_sync = TimeSync()

def get_now():
    return time_sync.get_synced_now()
