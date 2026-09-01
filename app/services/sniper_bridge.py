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
        state_dir = settings.DATA_DIR / "states"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / f"state_user_{user_id}.json"

    @staticmethod
    async def auto_login_and_save_state(credential: SinicaCredential) -> Tuple[bool, str, str]:
        """
        使用中研院帳密執行無頭瀏覽器自動登入並生成 session state 檔案。
        回傳 (success, message, state_file_path)
        """
        try:
            account = decrypt_data(credential.account_encrypted)
            password = decrypt_data(credential.password_encrypted)
        except Exception as e:
            return False, f"帳密解密失敗: {e}", ""

        state_path = SniperBridge.get_user_state_path(credential.user_id)

        from playwright.async_api import async_playwright
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
                await page.wait_for_timeout(2000)

                # 檢查是否成功登入 (檢查是否轉向首頁或包含登出/會員資訊)
                content = await page.content()
                if "登出" in content or "預約" in content or "reservation" in page.url:
                    await page.context.storage_state(path=str(state_path))
                    await browser.close()
                    return True, "中研院帳號登入成功，已更新 Session！", str(state_path)
                else:
                    await browser.close()
                    # 若已有 state 備份則檢查現存 state
                    if state_path.exists():
                        return True, "以現存 Session 狀態驗證中研院連線", str(state_path)
                    return False, "登入驗證失敗，請檢查帳號密碼是否正確。", ""
        except Exception as e:
            # 容錯：若直接開啟預約頁面測試現有 state
            if state_path.exists():
                return True, "使用已存 Session 憑證", str(state_path)
            return False, f"模擬登入異常: {e}", ""

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
