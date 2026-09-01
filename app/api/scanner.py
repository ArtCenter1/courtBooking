from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.config import settings
from app.models.user import User
from app.services.auth_service import get_current_user
from src.scanner import CalendarScanner
from src.auth import AuthManager
from src.notifier import Notifier

router = APIRouter(prefix="/api/scanner", tags=["場地時段雷達"])

@router.get("/slots")
async def scan_court_slots(
    court: str = Query("A", pattern="^[AB]$"),
    day: str = Query("05"),
    user: User = Depends(get_current_user)
):
    """
    即時查詢中研院網球場 A 或 B 於指定日期的時段開放狀態
    """
    config = {
        'system': {
            'url': settings.SINICA_GYM_URL,
            'state_file': "C:\\Users\\artce\\scripts\\state.json",
            'log_file': str(settings.LOGS_DIR / "scanner.log")
        }
    }
    notifier = Notifier(log_file=config['system']['log_file'])
    auth_mgr = AuthManager(config)
    scanner = CalendarScanner(config, auth_mgr, notifier)
    
    try:
        results = await scanner.scan_day_slots(target_day_num=day, court=court, headless=True)
        return {
            "court": court,
            "target_day": day,
            "data": results
        }
    except Exception as e:
        return {
            "court": court,
            "target_day": day,
            "error": str(e),
            "data": []
        }
