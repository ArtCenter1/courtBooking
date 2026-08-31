#!/usr/bin/env python3
"""
真相比對腳本：
- 方法 A：模擬 monitor 的方式，從 HTML 中爬出所有「開放」時段（regex）
- 方法 B：從即時 HTML 中讀取所有 .timeline__identity 的 title 與 class
- 比較兩者差異，找出 monitor 漏抓的真正原因
"""
import urllib.request
import ssl
import re
import json
from datetime import datetime, timedelta, timezone

TAIPEI_TZ = timezone(timedelta(hours=8))
URL = "https://gym.dga.sinica.edu.tw/reservation.html"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

now = datetime.now(TAIPEI_TZ)
target_date = (now + timedelta(days=5)).strftime('%m/%d')
print(f"📅 目標日期 (today+5): {target_date}")
print(f"📅 目標日期 (today+1): {(now + timedelta(days=1)).strftime('%m/%d')}")
print("=" * 70)

req = urllib.request.Request(URL, headers=HEADERS)
resp = urllib.request.urlopen(req, context=ctx, timeout=15)
html = resp.read().decode('utf-8')

print(f"HTML 大小: {len(html)} 字元")
print()

# === 方法 A：模擬 monitor 的正則 ===
print("【方法 A】Monitor 用的正則：title=\"HH:MM~HH:MM MM/DD開放\"")
pattern_a = r'title="(\d{2}:\d{2})~(\d{2}:\d{2})\s+(\d{2}/\d{2})開放"'
matches_a = re.findall(pattern_a, html)
print(f"  抓到 {len(matches_a)} 筆「開放」時段")
if matches_a:
    for start, end, date in matches_a[:30]:
        print(f"    {date} {start}~{end}")
print()

# === 方法 B：直接從 HTML 中找出所有 title 含 ~ 的時段 ===
print("【方法 B】所有含 ~ 的 title（不限「開放」）：")
pattern_b = r'title="(\d{2}:\d{2}~\d{2}:\d{2})[^"]*"'
matches_b = re.findall(pattern_b, html)
print(f"  抓到 {len(matches_b)} 筆含 ~ 的時段")
# 統計每種日期的時段數
date_count = {}
for t in matches_b:
    pass  # 只有時間沒日期
print()

# === 方法 C：找出每個 timeline__identity 的完整 attribute ===
print("【方法 C】所有 timeline__identity 元素的 title 與 class：")
pattern_c = r'<li[^>]*class="timeline__identity[^"]*"[^>]*title="([^"]+)"'
matches_c = re.findall(pattern_c, html)
print(f"  抓到 {len(matches_c)} 筆 timeline__identity")
if matches_c:
    # 統計
    class_pat = r'<li[^>]*class="(timeline__identity[^"]+)"[^>]*title="([^"]+)"'
    full = re.findall(class_pat, html)
    print(f"  含 class 的有 {len(full)} 筆")
    # 統計每種 class 的數量
    class_stats = {}
    for cls, ttl in full:
        # 提取關鍵 class
        key_cls = cls.replace('timeline__identity_', '').strip()
        class_stats.setdefault(key_cls, []).append(ttl)
    print()
    print("  各類別統計：")
    for cls, titles in sorted(class_stats.items()):
        print(f"    {cls}: {len(titles)} 筆")
        # 列出 target_date 的前 5 個
        relevant = [t for t in titles if target_date in t]
        if relevant:
            print(f"      其中 {target_date}: {len(relevant)} 筆")
            for t in relevant[:10]:
                print(f"        - {t}")
print()

# === 方法 D：直接抓含 target_date 的所有 title ===
print(f"【方法 D】HTML 中所有含「{target_date}」的 title/title-like 片段：")
relevant = re.findall(r'title="([^"]*' + re.escape(target_date) + r'[^"]*)"', html)
print(f"  抓到 {len(relevant)} 筆含 {target_date} 的 title")
for r in relevant[:20]:
    print(f"    - {r}")
print()

# === 方法 E：檢查是否有「已預約」之外的開放標示 ===
print("【方法 E】檢查其他可能的「可預約」標記：")
# 可能會有 no-open、available、open 等 class
class_pat_e = r'class="(timeline__identity[^"]*)"'
all_classes = re.findall(class_pat_e, html)
unique_classes = set(all_classes)
print(f"  所有出現過的 timeline__identity class：")
for c in sorted(unique_classes):
    count = all_classes.count(c)
    print(f"    {c}: {count} 次")
print()

# === 方法 F：搜尋 HTML 中是否有「non-sinica」相關標記 ===
print("【方法 F】搜尋 non-sinica（院外人士）的標記：")
non_sinica_count = len(re.findall(r'non-sinica', html))
print(f"  HTML 中出現 {non_sinica_count} 次 non-sinica")

# === 方法 G：檢查 09/01 是否有任何「開放」以外的時段顯示 ===
print()
print("【方法 G】09/01 所有時段狀態（不限開放關鍵字）：")
sep01 = re.findall(r'class="timeline__identity[^"]*"[^>]*title="([^"]*' + re.escape(target_date) + r'[^"]*)"', html)
print(f"  {target_date} 出現在 {len(sep01)} 個 title 中")
for t in sep01[:30]:
    print(f"    - {t}")
