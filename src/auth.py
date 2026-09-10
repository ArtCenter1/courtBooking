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
                ignore_https_errors=True,
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

                # 關鍵驗證：檢查是否真正處於登入狀態 (檢查是否有「登出」或「登入 / 註冊」)
                page_text = await page.inner_text('body')
                if "登出" in page_text or "Log out" in page_text or "Logout" in page_text:
                    await browser.close()
                    return True, "✅ Session 有效，確認處於登入狀態 (已識別登出按鈕)！"
                
                if "登入" in page_text or "Log in" in page_text:
                    await browser.close()
                    return False, "❌ Session 已過期 (目前為未登入訪客狀態，點擊時段將無反應)！請重新登入以更新 state.json。"

                # 備用檢查
                tennis_opt = page.locator('label:has-text("網球場")')
                if await tennis_opt.count() > 0:
                    await browser.close()
                    return False, "⚠️ 雖可載入日曆頁面，但未偵測到登入身分，點擊預約時段將無效！請重新登入。"

                await browser.close()
                return False, f"無法識別預約頁面元件 (當前 URL: {current_url})"
            except Exception as e:
                await browser.close()
                return False, f"驗證過程發生異常: {e}"
