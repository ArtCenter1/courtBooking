import asyncio
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.auth import AuthManager
from src.scanner import CalendarScanner
from src.notifier import Notifier
from app.config import settings

async def main():
    config = {
        'system': {
            'url': settings.SINICA_GYM_URL,
            'state_file': str(BASE_DIR / "state.json"),
            'log_file': str(settings.LOGS_DIR / "test_scanner.log")
        }
    }
    notifier = Notifier(log_file=config['system']['log_file'])
    auth_mgr = AuthManager(config)
    scanner = CalendarScanner(config, auth_mgr, notifier)
    
    print("Testing scanning Court A for day 08...")
    res = await scanner.scan_day_slots(target_day_num="08", court="A", headless=True)
    print(f"Result count: {len(res)}")
    for day in res:
        if day.get('isTarget'):
            print(f"Target day: {day.get('dayNum')}, total slots: {len(day.get('slots', []))}")
            for slot in day.get('slots', []):
                print(f"  Slot: title={slot.get('title')}, text={slot.get('text')}, isBooked={slot.get('isBooked')}, isOpenPending={slot.get('isOpenPending')}")

if __name__ == '__main__':
    asyncio.run(main())
