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
- **[2026-09-07] 100% 復刻中研院體育館日曆規格**:
  - 七欄兩週 × 雙子欄 (每週 7 天，每天 16 時段，偶數時段左、奇數時段右)。
  - 院內同仁、院外人士、團體、休館時段皆呈現預設箭頭 (`cursor: default; pointer-events: none;`)，無法被點選。
  - 僅符合院外人士可預約的時段呈現手型指針 (`cursor: pointer;`) 並可加入優先志願。
  - 臨時解除放票與即將開放時段採用 `@keyframes pulse-attention` 金黃色閃爍發光醒目提示，滑鼠 hover 呈現詳細開放日期時間資訊 (例如 `09/08 00:00 開放`)。

---

## 📌 當前任務 (Current Tasks)
- `[x]` 後端: 實作 `scan_full_calendar` 與 `POST /api/scanner/full-radar` 端點。
- `[x]` 前端: 復刻中研院體育館日曆樣式 (顏色、七欄雙子欄、時段標籤)。
- `[x]` 互動: 嚴格區分可預約 (手型可點) 與他人已預約 (原始箭頭不可點)。
- `[x]` 動畫: 未來開放時段閃爍高亮提醒 + hover 浮現放票時間。
- `[x]` 測試: 通過全套測試與即時截圖驗證。

## ⚠️ 已知阻礙與注意事項
- 中研院放票時空位 class 帶有 `timeline__identity_no-open`，切勿以此 class 作為未開放判斷。
- 00:00:00 伺服器放票後，時段按鈕文字會由 `MM/DD開放` 轉變為 `17~18` 等時段縮寫。
