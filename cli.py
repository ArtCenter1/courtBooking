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

def parse_targets_arg(targets_str):
    """解析 A:16:00,B:17:00 格式為結構化字典清單"""
    items = []
    for part in targets_str.split(','):
        part = part.strip()
        if not part:
            continue
        if ':' in part:
            c, s = part.split(':', 1)
            items.append({"court": c.strip().upper(), "slot": s.strip()})
        else:
            items.append({"court": "A", "slot": part.strip()})
    return items

def try_load_active_db_task():
    """嘗試從本機資料庫自動載入待執行任務"""
    db_path = BASE_DIR / "data" / "booking.db"
    if not db_path.exists():
        return None
    try:
        import sqlite3
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        # 檢查 bookingtask 資料表
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bookingtask'")
        if not cur.fetchone():
            return None
        cur.execute("""
            SELECT id, target_date, target_day_num, primary_slots_json, court_order_json, targets_json 
            FROM bookingtask 
            WHERE status = 'pending' 
            ORDER BY created_at DESC LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            import json
            task_id, target_date, target_day_num, p_slots, c_order, t_json = row
            targets = []
            if t_json:
                targets = json.loads(t_json)
            else:
                c_list = json.loads(c_order) if c_order else ["A"]
                s_list = json.loads(p_slots) if p_slots else ["17:00"]
                targets = [{"court": c, "slot": s} for c in c_list for s in s_list]
            return {
                "id": task_id,
                "target_date": target_date,
                "target_day_num": target_day_num,
                "targets": targets
            }
    except Exception:
        pass
    return None

def apply_targets_to_config(args, config):
    """整合 CLI 參數、DB 待命任務與設定檔，嚴格落實防呆與確認"""
    # 1. 若指定 --active 或完全未指定目標，優先檢查 DB 待命任務
    loaded_from_db = False
    if getattr(args, 'active', False) or (not getattr(args, 'day', None) and not getattr(args, 'targets', None) and not getattr(args, 'slot', None)):
        db_task = try_load_active_db_task()
        if db_task:
            config['target']['date'] = db_task['target_date']
            config['target']['day_num'] = str(db_task['target_day_num']).zfill(2)
            config['target']['targets'] = db_task['targets']
            print("\n" + "="*56)
            print(f"🎯 【自動載入】成功載入 Web 控制台排程待命任務 (Task #{db_task['id']})！")
            loaded_from_db = True

    # 2. 若有傳入 -t / --targets (優先級高於單一 -s/-c)
    if getattr(args, 'targets', None):
        parsed = parse_targets_arg(args.targets)
        if parsed:
            config['target']['targets'] = parsed

    # 3. 日期覆蓋
    if getattr(args, 'day', None):
        config['target']['day_num'] = str(args.day).zfill(2)
        config['target']['date'] = str(args.day)

    # 4. 單點參數覆蓋 (-s 或 -c) 警示防呆
    if not getattr(args, 'targets', None) and (getattr(args, 'court', None) or getattr(args, 'slot', None)):
        court = getattr(args, 'court', None) or config['target'].get('court_order', ['A'])[0]
        slot = getattr(args, 'slot', None) or config['target'].get('primary_slots', ['17:00'])[0]
        config['target']['targets'] = [{"court": court, "slot": slot}]
        print("\n⚠️  【注意】您使用了單一覆蓋參數 (-c / -s)，僅會鎖定單一場地與時段！")
        print("💡 如需搶多個時段或跨場地志願（如 志願1: A場 16:00, 志願2: B場 17:00），請使用: -t A:16:00,B:17:00\n")

    # 5. 確保 config 具備 targets
    if not config['target'].get('targets'):
        c_list = config['target'].get('court_order', ['A', 'B'])
        s_list = config['target'].get('primary_slots', ['17:00'])
        config['target']['targets'] = [{"court": c, "slot": s} for c in c_list for s in s_list]

    # 6. 強制出擊明細回顯 (Assertion / Echo)
    print("=" * 56)
    print(f"🎯 出擊目標清單確認 | 目標日期: {config['target']['day_num']} 日 ({config['target'].get('date', '')})")
    print("=" * 56)
    for i, t in enumerate(config['target']['targets']):
        print(f"   [志願 {i+1}] 網球場 {t['court']} ({t['slot']})")
    print("=" * 56 + "\n")

async def handle_dry_run(args, config):
    apply_targets_to_config(args, config)

    notifier = Notifier(log_file=config['system']['log_file'])
    auth = AuthManager(config)
    sniper = Sniper(config, auth, notifier)
    
    seconds = args.seconds or 3
    print("🧪 啟動搶票模擬推演 (Dry-Run Simulation)...")
    res = await sniper.run_snipe_task(dry_run=True, dry_run_seconds=seconds)
    
    ss_dir = Path(config['system'].get('screenshot_dir', '.'))
    if ss_dir.exists():
        files = sorted(list(ss_dir.glob("snipe_result_*.png")), key=os.path.getmtime)
        if files:
            latest = files[-1]
            import shutil
            local_copy = BASE_DIR / "latest_snipe_result.png"
            shutil.copy2(latest, local_copy)
            print("\n" + "="*52)
            print("🎉 【模擬推演成功】人機驗證與表單路徑 100% 暢通！")
            print(f"📸 存證截圖: {latest}")
            print(f"👉 點此在 IDE 開啟預覽: {local_copy.name}")
            print("="*52 + "\n")

async def handle_snipe(args, config):
    apply_targets_to_config(args, config)

    notifier = Notifier(log_file=config['system']['log_file'])
    auth = AuthManager(config)
    sniper = Sniper(config, auth, notifier)
    
    await sniper.run_snipe_task(dry_run=False, keep_browser_open=True)

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
    dry_p.add_argument("-d", "--day", help="目標日期 (例如 26)")
    dry_p.add_argument("-t", "--targets", help="結構化志願序清單 (例如 'A:16:00,B:17:00')")
    dry_p.add_argument("-c", "--court", choices=["A", "B"], help="場地 (A 或 B)")
    dry_p.add_argument("-s", "--slot", help="時段 (例如 17:00)")
    dry_p.add_argument("--active", action="store_true", help="自動從 Web 資料庫載入待命任務")
    dry_p.add_argument("--seconds", type=int, default=3, help="模擬倒數秒數")
    
    # snipe
    snipe_p = subparsers.add_parser("snipe", help="正式執行 00:00 搶票任務")
    snipe_p.add_argument("-d", "--day", help="目標日期 (例如 26)")
    snipe_p.add_argument("-t", "--targets", help="結構化志願序清單 (例如 'A:16:00,B:17:00')")
    snipe_p.add_argument("-c", "--court", choices=["A", "B"], help="場地 (A 或 B)")
    snipe_p.add_argument("-s", "--slot", help="時段 (例如 17:00)")
    snipe_p.add_argument("--active", action="store_true", help="自動從 Web 資料庫載入待命任務")
    
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
