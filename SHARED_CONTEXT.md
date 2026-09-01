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
- **[2026-09-01] SaaS 架構選型**: 採用 FastAPI + SQLite/SQLModel + Modern Responsive SPA 前端 + PWA，兼具極簡卡片時段選擇與摺疊進階微調。
- **[2026-09-01] 憑證安全**: 採用 AES-256 加密儲存中研院帳密，搶票前 10 分鐘自動模擬登入換發 Session。

## ⚠️ 已知阻礙與注意事項
- 中研院放票時空位 class 帶有 `timeline__identity_no-open`，切勿以此 class 作為未開放判斷。
- 00:00:00 伺服器放票後，時段按鈕文字會由 `MM/DD開放` 轉變為 `17~18` 等時段縮寫。
