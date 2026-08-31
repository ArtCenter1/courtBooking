"""
中研院體育館預約系統統一命令列入口 (Unified CLI)
支援 session 檢查、時鐘校驗、頁面時段掃描、模擬推演 (dry-run) 與正式 00:00 搶票。
"""

import os
import sys
import yaml
import asyncio
import argparse
from pathlib import Path

# 加入專案目錄至 sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Windows 控制台 UTF-8 編碼支援
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.time_sync import time_sync, get_now
from src.notifier import Notifier
from src.auth import AuthManager
from src.scanner import CalendarScanner
from src.sniper import Sniper

def load_config(config_path="config/config.yaml"):
    full_path = BASE_DIR / config_path
    if not full_path.exists():
        print(f"❌ 找不到設定檔: {full_path}")
        sys.exit(1)
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def handle_check(args, config):
    notifier = Notifier(log_file=config['system']['log_file'])
    auth = AuthManager(config)
    
    print("==========================================")
    print("🔍 系統環境與 Session 健康度檢查")
    print("==========================================")
    
    # 1. 檢查 state.json
    state_file = auth.state_file
    print(f"1. 狀態檔路徑: {state_file}")
    if not auth.check_state_file_exists():
        print("❌ 狀態檔不存在！請先執行 save_state.py 建立登入狀態。")
        return
    print("✅ 狀態檔存在。")

    # 2. 時鐘校準
    ok, drift, method = time_sync.calibrate()
    if ok:
        print(f"2. 時鐘校準: 成功 (漂移量: {drift:+.3f} 秒, 來源: {method})")
        print(f"   標準台北時間: {get_now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    else:
        print(f"⚠️ 時鐘校準警告: {method}，將使用本機時鐘。")

    # 3. 測試登入有效性
    print("3. 正在開啟背景瀏覽器驗證中研院預約 Session...")
    is_valid, msg = await auth.verify_session_health(headless=True)
    if is_valid:
        print(f"✅ {msg}")
        print("🎉 系統一切就緒，可隨時執行搶票任務！")
    else:
        print(f"❌ {msg}")
        print("⚠️ 請重新執行 save_state.py 登入以更新 Session！")

async def handle_scan(args, config):
    notifier = Notifier(log_file=config['system']['log_file'])
    auth = AuthManager(config)
    scanner = CalendarScanner(config, auth, notifier)
    
    day_target = args.day or config['target']['day_num']
    court = args.court or "A"
    
    print(f"🔍 正在掃描網球場 {court} 於 {day_target} 日的時段狀態...")
    results = await scanner.scan_day_slots(target_day_num=day_target, court=court, headless=True)
    
    target_found = False
    for day in results:
        if day['isTarget']:
            target_found = True
            print(f"\n📅 日期區塊: {day['rawHeader']} (日: {day['dayNum']})")
            print("-" * 50)
            for slot in day['slots']:
                status_icon = "🔴" if slot['isBooked'] else ("🟡" if slot['isOpenPending'] else "🟢")
                print(f"  {status_icon} {slot['title']:<25} | 狀態: {slot['text']:<12} | 標記: {slot['class']}")
            print("-" * 50)
    
    if not target_found:
        print(f"⚠️ 未在目前日曆視圖中找到 {day_target} 日，請確認是否需翻頁或切換視圖。")

async def handle_dry_run(args, config):
    notifier = Notifier(log_file=config['system']['log_file'])
    auth = AuthManager(config)
    sniper = Sniper(config, auth, notifier)
    
    seconds = args.seconds or 5
    print("==========================================")
    print("🧪 啟動搶票模擬推演 (Dry-Run Simulation)")
    print(f"⏱️ 將在 {seconds} 秒倒數後模擬 00:00 搶票全流程")
    print("==========================================")
    await sniper.run_snipe_task(dry_run=True, dry_run_seconds=seconds)

async def handle_snipe(args, config):
    notifier = Notifier(log_file=config['system']['log_file'])
    auth = AuthManager(config)
    sniper = Sniper(config, auth, notifier)
    
    await sniper.run_snipe_task(dry_run=False)

def main():
    parser = argparse.ArgumentParser(description="中研院體育館網球場自動化搶票系統")
    parser.add_argument("--config", default="config/config.yaml", help="指定設定檔路徑")
    
    subparsers = parser.add_subparsers(dest="command", help="子指令")
    
    # check
    subparsers.add_parser("check", help="檢查 session 與環境就緒狀態")
    
    # scan
    scan_p = subparsers.add_parser("scan", help="掃描日曆時段狀態")
    scan_p.add_argument("--day", help="目標日期數字 (例如 05)")
    scan_p.add_argument("--court", choices=["A", "B"], help="場地 A 或 B")
    
    # dry-run
    dry_p = subparsers.add_parser("dry-run", help="模擬推演 00:00 搶票流程")
    dry_p.add_argument("--seconds", type=int, default=5, help="模擬倒數秒數")
    
    # snipe
    subparsers.add_parser("snipe", help="正式執行 00:00 搶票任務")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    config = load_config(args.config)
    
    if args.command == "check":
        asyncio.run(handle_check(args, config))
    elif args.command == "scan":
        asyncio.run(handle_scan(args, config))
    elif args.command == "dry-run":
        asyncio.run(handle_dry_run(args, config))
    elif args.command == "snipe":
        asyncio.run(handle_snipe(args, config))

if __name__ == "__main__":
    main()
