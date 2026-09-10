import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any

from app.config import settings
from app.models.booking_task import BookingTask
from app.models.credential import SinicaCredential
from app.services.crypto import decrypt_data
from src.sniper import Sniper
from src.scanner import CalendarScanner
from src.auth import AuthManager
from src.notifier import Notifier

class SniperBridge:
    @staticmethod
    def get_user_state_path(user_id: int) -> Path:
        # 優先使用 save_state.py 建立的主 state.json
        external_state = Path(r"C:\Users\artce\scripts\state.json")
        if external_state.exists():
            return external_state
        local_state = settings.BASE_DIR / "state.json"
        if local_state.exists():
            return local_state

        state_dir = settings.DATA_DIR / "states"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / f"state_user_{user_id}.json"

    @staticmethod
    async def auto_login_and_save_state(credential: SinicaCredential) -> Tuple[bool, str, str]:
        """
        驗證現存 Session 狀態，若失效才嘗試自動登入。
        嚴格禁止將未通過驗證的訪客狀態覆蓋為有效 Session！
        """
        state_path = SniperBridge.get_user_state_path(credential.user_id)

        from playwright.async_api import async_playwright
        
        # 步驟 1：先檢測現存 Session 是否依然有效
        if state_path.exists():
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(
                        storage_state=str(state_path),
                        ignore_https_errors=True
                    )
                    page = await context.new_page()
                    await page.goto(settings.SINICA_GYM_URL, wait_until="networkidle", timeout=12000)
                    page_text = await page.inner_text('body')
                    await browser.close()
                    
                    if "登出" in page_text or "Log out" in page_text or "Logout" in page_text:
                        return True, "現存 Session 狀態驗證有效（已具備登出權限）", str(state_path)
            except Exception as e:
                pass

        # 步驟 2：現存 Session 無效，嘗試以帳密進行登入
        try:
            account = decrypt_data(credential.account_encrypted)
            password = decrypt_data(credential.password_encrypted)
        except Exception as e:
            return False, f"帳密解密失敗: {e}", ""

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                login_url = "https://gym.dga.sinica.edu.tw/login.html"
                await page.goto(login_url, wait_until="networkidle")

                # 輸入帳號密碼
                await page.fill('input[type="text"], input[name*="user"], input[id*="user"]', account)
                await page.fill('input[type="password"]', password)
                
                # 點擊登入按鈕
                submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("登入")')
                await submit_btn.first.click()
                await page.wait_for_timeout(3000)

                # 嚴格驗證：必須明確出現「登出」字樣，嚴禁使用「預約」或 URL 模糊比對！
                page_text = await page.inner_text('body')
                if "登出" in page_text or "Log out" in page_text or "Logout" in page_text:
                    save_target = settings.DATA_DIR / "states" / f"state_user_{credential.user_id}.json"
                    save_target.parent.mkdir(parents=True, exist_ok=True)
                    await page.context.storage_state(path=str(save_target))
                    await browser.close()
                    return True, "中研院帳號自動登入成功，已換發 Session！", str(save_target)
                else:
                    await browser.close()
                    return False, "自動登入未偵測到「登出」按鈕，可能需要手動驗證！請執行 save_state.py", ""
        except Exception as e:
            return False, f"自動登入異常: {e}。請執行 save_state.py 手動登入。", ""

    @staticmethod
    async def execute_task(task: BookingTask, state_path: str, dry_run: bool = False, dry_run_seconds: int = 5) -> Dict[str, Any]:
        """
        執行單一搶票任務（可為 dry-run 或實戰）
        """
        log_file = str(settings.LOGS_DIR / f"task_{task.id}_{datetime.now().strftime('%Y%m%d')}.log")
        notifier = Notifier(log_file=log_file)
        
        # 構造專屬 config
        config = {
            'target': {
                'date': task.target_date,
                'day_num': task.target_day_num,
                'primary_slots': task.primary_slots,
                'court_order': task.court_order,
                'fallback_time_range': {
                    'min_hour': task.fallback_min_hour,
                    'max_hour': task.fallback_max_hour
                }
            },
            'system': {
                'url': settings.SINICA_GYM_URL,
                'state_file': state_path,
                'log_file': log_file,
                'screenshot_dir': str(settings.SCREENSHOT_DIR),
                'refresh_attempts': task.refresh_attempts,
                'refresh_interval_ms': task.refresh_interval_ms
            },
            'time_sync': {
                'enabled': True,
                'ntp_server': "time.stdtime.gov.tw",
                'fallback_http_url': settings.SINICA_GYM_URL
            },
            'telegram': {
                'enabled': bool(task.telegram_bot_token and task.telegram_chat_id),
                'bot_token': task.telegram_bot_token or "",
                'chat_id': task.telegram_chat_id or ""
            }
        }
        
        import importlib
        import src.sniper
        importlib.reload(src.sniper)
        from src.sniper import Sniper

        auth_mgr = AuthManager(config)
        sniper = Sniper(config, auth_mgr, notifier)
        
        success = await sniper.run_snipe_task(dry_run=dry_run, dry_run_seconds=dry_run_seconds)
        
        # 尋找產生的截圖
        screenshot_file = None
        screenshots = sorted(list(settings.SCREENSHOT_DIR.glob("snipe_result_*.png")), key=os.path.getmtime)
        if screenshots:
            screenshot_file = str(screenshots[-1].name)
            
        return {
            "success": success,
            "log_file": log_file,
            "screenshot": screenshot_file
        }
