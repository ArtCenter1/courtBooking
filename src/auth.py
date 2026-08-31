"""
登入驗證與 Session 管理模組 (Auth & Session Manager)
檢查 state.json 檔案狀態、驗證當前 Session 是否有效。
"""

import os
from pathlib import Path
from playwright.async_api import async_playwright

class AuthManager:
    def __init__(self, config):
        self.config = config
        self.state_file = self._resolve_state_file()

    def _resolve_state_file(self):
        """依序搜尋主 state_file 與備用 state_backup_file"""
        primary = self.config['system'].get('state_file')
        backup = self.config['system'].get('state_backup_file')
        if primary and os.path.exists(primary):
            return primary
        if backup and os.path.exists(backup):
            return backup
        return primary

    def check_state_file_exists(self):
        return self.state_file and os.path.exists(self.state_file)

    async def verify_session_health(self, headless=True):
        """
        啟動瀏覽器檢測 Session 是否依然有效
        返回 (is_valid, message)
        """
        if not self.check_state_file_exists():
            return False, f"找不到 state.json 狀態檔: {self.state_file}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                storage_state=self.state_file,
                locale='zh-TW'
            )
            page = await context.new_page()
            try:
                target_url = self.config['system']['url']
                response = await page.goto(target_url, wait_until="networkidle", timeout=15000)
                current_url = page.url
                
                # 檢查是否被重定向到登入頁面
                if "login" in current_url.lower():
                    await browser.close()
                    return False, f"Session 已過期，頁面重定向至登入頁: {current_url}"

                # 檢查網球場選單或關鍵元素是否存在
                tennis_opt = page.locator('label:has-text("網球場")')
                if await tennis_opt.count() > 0:
                    await browser.close()
                    return True, "✅ Session 有效，成功識別預約系統元素！"
                
                # 若找不到網球場文字，再次確認是否有預約日曆表格
                calendar_items = page.locator('.calendar__day-item')
                if await calendar_items.count() > 0:
                    await browser.close()
                    return True, "✅ Session 有效，成功載入日曆表格！"

                await browser.close()
                return False, f"無法識別預約頁面元件 (當前 URL: {current_url})"
            except Exception as e:
                await browser.close()
                return False, f"驗證過程發生異常: {e}"
