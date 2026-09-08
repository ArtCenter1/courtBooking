from typing import Optional, List
import os
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from pydantic import BaseModel

from app.config import settings
from app.database import get_session
from app.models.user import User
from app.models.credential import SinicaCredential
from app.services.auth_service import get_current_user
from app.services.sniper_bridge import SniperBridge
from src.scanner import CalendarScanner
from src.auth import AuthManager
from src.notifier import Notifier

router = APIRouter(prefix="/api/scanner", tags=["場地時段雷達"])

class RadarRequest(BaseModel):
    court: str = "ALL"
    day: str = "05"
    requested_slots: List[str] = []

@router.post("/slots")
async def scan_court_slots(
    req: RadarRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    即時雷達：掃描中研院網球場於指定日期的時段開放狀態，並比對志願時段
    """
    # 決定使用哪個 state_file
    # 優先使用該 user 的 state file
    state_file_path = str(SniperBridge.get_user_state_path(user.id))
    if not os.path.exists(state_file_path):
        # 降級使用全域 state.json (若存在)
        state_file_path = str(settings.BASE_DIR / "state.json")
        
    config = {
        'system': {
            'url': settings.SINICA_GYM_URL,
            'state_file': state_file_path,
            'log_file': str(settings.LOGS_DIR / "scanner.log")
        }
    }
    notifier = Notifier(log_file=config['system']['log_file'])
    auth_mgr = AuthManager(config)
    scanner = CalendarScanner(config, auth_mgr, notifier)
    
    try:
        results = await scanner.scan_day_slots(target_day_num=req.day, court=req.court, headless=True)
        
        # 解析與比對
        matched_open_slots = []
        all_open_slots = []
        
        # 若 court=ALL，results 是一個 dict: {'A': [...], 'B': [...]}
        # 若是單一 court，則是一個 array [...]
        courts_data = {}
        if req.court == 'ALL':
            courts_data = results
        else:
            courts_data = {req.court: results}
            
        for c_name, days_list in courts_data.items():
            for day_info in days_list:
                if not day_info.get('isTarget'):
                    continue
                
                for slot in day_info.get('slots', []):
                    # 如果該時段可直接預約
                    if slot.get('isAvailable'):
                        slot_info = {
                            "court": c_name,
                            "startTime": slot.get('startTime'),
                            "title": slot.get('title'),
                            "text": slot.get('text')
                        }
                        all_open_slots.append(slot_info)
                        
                        # 檢查是否符合志願
                        if slot.get('startTime') in req.requested_slots:
                            matched_open_slots.append(slot_info)

        return {
            "success": True,
            "target_day": req.day,
            "courts_data": courts_data,
            "all_open_slots": all_open_slots,
            "matched_open_slots": matched_open_slots,
            "has_matching_available": len(matched_open_slots) > 0
        }
    except Exception as e:
        return {
            "success": False,
            "target_day": req.day,
            "error": str(e),
            "courts_data": {}
        }

class FullRadarRequest(BaseModel):
    view_mode: Optional[str] = "two_weeks" # 'two_weeks' | 'current_month'
    nav_action: Optional[str] = None       # 'prev_month' | 'next_month' | 'two_weeks' | 'current_month'

@router.post("/full-radar")
async def scan_full_radar(
    req: Optional[FullRadarRequest] = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    全域雷達：掃描未來兩週/整月份日曆格 A/B 兩場地的所有時段開放狀態
    支援即時點擊中研院官方工具列（上個月、下個月、當月、兩週內）
    """
    req_view_mode = req.view_mode if req else "two_weeks"
    req_nav_action = req.nav_action if req else None

    state_file_path = str(SniperBridge.get_user_state_path(user.id))
    if not os.path.exists(state_file_path):
        state_file_path = str(settings.BASE_DIR / "state.json")
        
    config = {
        'system': {
            'url': settings.SINICA_GYM_URL,
            'state_file': state_file_path,
            'log_file': str(settings.LOGS_DIR / "scanner.log")
        }
    }
    notifier = Notifier(log_file=config['system']['log_file'])
    auth_mgr = AuthManager(config)
    scanner = CalendarScanner(config, auth_mgr, notifier)
    
    try:
        matrix = await scanner.scan_full_calendar(
            headless=True,
            view_mode=req_view_mode,
            nav_action=req_nav_action
        )
        return {
            "success": True,
            "matrix": matrix
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "matrix": {"A": [], "B": []}
        }

