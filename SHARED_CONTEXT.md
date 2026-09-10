# SHARED_CONTEXT — 中研院網球場預約系統 (courtBooking)

## 📌 當前里程碑與進度
- **當前版本**：`v0.1.0-alpha` (Release Tag & `stable-alpha` 分支已備份至 GitHub)
- **已完成工作**：
  - 核心模組化重構 (`src/` 包含 `auth.py`, `sniper.py`, `scanner.py`, `time_sync.py`, `notifier.py`)。
  - 完成毫秒級時鐘校準 (NTP/HTTP Date)，補償本機時鐘漂移。
  - 修復中研院放票時段判定 Bug（移除 `no-open` class 誤判，放票文字變更為時段時立即秒點預約）。
  - 建立專屬測試與推演腳本 (`tests/test_simulation.py`, `tests/inspect_slots.py`)。
  - 完成多使用者 SaaS 架構規劃 (`/grill-me` 訪談完成，產生 `implementation_plan.md`)。

## 🎯 當前任務
- **SaaS 升級 Phase 1**：建置基於 FastAPI + 現代響應式前端 SPA 的多租戶任務排程系統。
- **作戰保證**：保持現有 CLI 入口 (`cli.py`) 永遠隨時可獨立直接執行實戰搶票。

## 📋 決策記錄 (Decisions)
- **[2026-09-01] Release v0.1.0-alpha**: 將具備時鐘校準與已修復 Bug 的 CLI 模組封裝為 alpha 版本並推送獨立分支保護。
- **[2026-09-01] SaaS 架構選型**: 採用 FastAPI + SQLite/SQLModel + JWT 認證 + Playwright (SniperBridge)。
- **[2026-09-07] Live Radar 雷達 API**: 後端 `src/scanner.py` 新增 `scan_day_slots()` 與 `scan_full_calendar()` 方法，支援全域日曆與 A/B 場地解析。
- **[2026-09-07] 全新「掃描優先 (Scan-First)」UX 流程**: 改為「1. 點擊全域掃描 -> 2. 顯示未來兩週完整空位地圖 (可預約🟢/即將開放🟡/已預約🔴) -> 3. 點選志願順序 (①②③) -> 4. 制定腳本進入待命 -> 5. 執行並回報」之工作流。
- **[2026-09-09] 官方日曆即時導航 (方案 B)**:
  - 在 `src/scanner.py` 新增 `nav_action` 與 `view_mode` 支援，後端透過 Playwright 模擬點擊官方工具列。
  - 前端工具列按鈕（`‹`、`›`、`當月`、`兩週內`）綁定即時 AJAX 切換，支援動態載入完整當月 30~31 天日曆或切換次月。
- **[2026-09-10] 二段式預約流程與 reCAPTCHA v2 自動穿透**:
  - 實證中研院預約流程並非舊版 in-page 彈窗，點擊時段後跳轉獨立「場地預約 Reservation」表單頁。
  - 表單頁底端設有 Google reCAPTCHA v2 核取方塊（我不是機器人），實戰確認高信任 session 點擊後直接呈現綠色打勾（無圖片挑戰題）。
  - 重構 `src/sniper.py` 支援毫秒級二段式預約：時段點擊 -> 穿透 reCAPTCHA iframe 秒點 `#recaptcha-anchor` -> 偵測打勾 -> 極速點擊「預約 Reserve」送出。
  - 支援多時段預約連鎖回航（`_ensure_on_calendar`）。
- **[2026-09-10] 雙軌並行 UX（待命 vs 模擬測試）**:
  - 前端策略卡片（Step 3）將原本單一待命按鈕重構為並排雙軌：
    - `🎯 制定腳本並進入待命`：正式儲存任務，排程系統於 23:50 自動預熱並於 00:00 發動實戰。
    - `🧪 模擬測試 (Dry-Run)`：維持完全相同時段選定流程，一鍵觸發 3 秒倒數與第二階段 reCAPTCHA 自動驗證推演，彈窗即時展示推演日誌與截圖存證，嚴格攔截送出按鈕防止誤訂。
- **[2026-09-10] 修復 Sniper 多場地 court_order 與推演截圖鎖定**:
  - 修復 `sniper.py` 過去硬編碼首選預約 A 場之歷史瑕疵，現全面依據使用者設定之 `court_order`（如 B 場優先）即時切換標籤頁並發動預約。
  - 明確區分截圖對象：Dry-Run 模式下於第二階段表單頁面直接截取「reCAPTCHA 打勾通過（綠勾）」畫面；正式搶票則於衝刺完成後截取日曆最終成功/失敗大局結果。

- **[2026-09-10] 修復 Session 偽有效驗證與未登入時段點擊無效問題**:
  - 中研院預約日曆在「未登入（訪客身份）」下依然可完整瀏覽日曆與時段，但前端與後端會靜默忽略對可預約時段的點擊（無法跳轉至預約表單）。
  - 原 `auth.verify_session_health` 僅檢查日曆與「網球場」標籤是否存在，導致過期的 `state.json` 被誤判為「有效」。現已修正為嚴格檢驗頁面是否存在「登出」按鈕，若為訪客則明確報錯。
  - 根目錄提供全新 `save_state.py`，開啟瀏覽器後自動監聽使用者登入並即時儲存 `state.json`。
- **[2026-09-11] 徹底修復排程器預熱自動登入假陽性覆蓋 Session 致命 Bug**:
  - 排程器於 23:50:00 預熱時曾因 `if "登出" in content or "預約" in content` 命中首頁常駐「預約」字樣，將無頭未登入狀態誤判為成功並覆蓋狀態檔，導致 00:00 搶票時以訪客身分點擊靜態 `<div>` 失效。
  - 徹底移除模糊判定，`SniperBridge` 優先沿用經 `save_state.py` 驗證具備「登出」權限的實體 Session，嚴禁背景無頭登入隨意覆蓋。
  - `Sniper.run_snipe_task` 載入頁面後第一時間強制校驗「登出」標籤，若處於訪客態立即終止報錯，絕不盲目倒數。

---

## 📌 當前任務 (Current Tasks)
- `[x]` 後端: 實作 `scan_full_calendar` 與 `POST /api/scanner/full-radar` 端點。
- `[x]` 前端: 復刻中研院體育館日曆樣式 (顏色、七欄雙子欄、時段標籤)。
- `[x]` 互動: 嚴格區分可預約 (手型可點) 與他人已預約 (原始箭頭不可點)。
- `[x]` 動畫: 未來開放時段閃爍高亮提醒 + hover 浮現放票時間。
- `[x]` 導航: 完成方案 B（‹ 上個月 / › 下個月 / 當月整月 / 兩週內）即時點擊連線切換。
- `[x]` 測試: 通過全套測試與即時截圖驗證。
- `[x]` 核心: 升級 `src/sniper.py` 二段式預約與 reCAPTCHA v2 自動穿透，通過 dry-run 衝刺推演。
- `[x]` 驗證: 修正 `auth.py` 登入健康檢查，提供 `save_state.py` 一鍵更新 Session。
- `[x]` 穩定: 修正 `sniper_bridge.py` 與 `sniper.py` 訪客登入假陽性阻斷機制。

## ⚠️ 已知阻礙與注意事項
- 中研院放票時空位 class 帶有 `timeline__identity_no-open`，切勿以此 class 作為未開放判斷。
- 00:00:00 伺服器放票後，時段按鈕文字會由 `MM/DD開放` 轉變為 `17~18` 等時段縮寫。
- **未登入狀態下日曆可視但點擊完全無效**：日曆開放時段會被渲染為靜態 `<div>`，必須確保 `state.json` 有效登入（存在「登出」字樣），否則點擊時段不會跳轉表單。
- 預約流程為跳轉式獨立表單頁面（`場地預約 Reservation`），表單包含 Google reCAPTCHA v2 核取方塊，必須等待綠勾確認後點擊「預約 Reserve」才算完成。
- **背景排程預熱絕不可盲目以無頭帳密覆蓋 Session**，中研院入口極易觸發隱形驗證，必須以手動驗證之 `state.json` 為單一真理源。
