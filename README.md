# 中研院體育館網球場預約自動化系統 (方案 A 重構版)

## 專案說明
這是一套專為中研院綜合體育館網球場（`https://gym.dga.sinica.edu.tw/reservation.html`）設計的**智慧自動預約 SaaS 平台與毫秒級極速搶票系統**。
支援院外人士提前 5 天（00:00:00 開放）之搶票任務，提供**現代化 Web 響應式控制面板（手機 PWA / 桌面電腦）**，具備 AES-256 憑證安全金庫、多租戶志願序排程與防衝突分流避讓、毫秒級 NTP/HTTP 校時、自動 23:50 預熱 Session 與即時結果截圖存證。

---

## 🌟 啟動方式 (SaaS 網頁版 & CLI 命令列)

### 方式 A：啟動 Web SaaS 視覺化平台 (推薦)
```cmd
python run_server.py
```
- 開啟瀏覽器訪問：`http://127.0.0.1:8000`
- 支援手機或電腦瀏覽器操作、卡片式快速選擇日期與時段、志願序設定、進階精密微調與一鍵推演 (Dry-Run)。
- 後端 API 文件：`http://127.0.0.1:8000/docs`

### 方式 B：單機 CLI 快速執行
```cmd
python cli.py check                    # 檢查 Session 與時鐘校準
python cli.py scan --court A --day 05  # 掃描指定日期空位狀態
python cli.py dry-run --seconds 5      # 模擬推演 5 秒倒數搶票
python cli.py snipe                   # 正式 00:00 搶票守候任務
```

---

## 核心架構與模組

```
courtBooking/
├── app/                     # [SaaS 雲端層] FastAPI + 響應式 Web 前端
│   ├── main.py              # FastAPI 進入點與靜態資源託管
│   ├── config.py            # SaaS 系統設定與安全金庫金鑰
│   ├── database.py          # 資料庫連線 (SQLModel / SQLite)
│   ├── models/              # User, SinicaCredential, BookingTask 資料模型
│   ├── api/                 # 認證、憑證、任務管理與雷達掃描 API
│   ├── services/            # AES-256 加密、JWT、背景排程與搶票 Worker 調度
│   └── static/              # 現代化深色響應式前端 SPA (HTML / CSS / JS)
├── src/                     # [搶票引擎核心]
│   ├── time_sync.py         # 毫秒級時間同步模組 (SNTP + HTTP Date)
│   ├── auth.py              # Session 健康度預檢與狀態管理
│   ├── scanner.py           # 日曆與時段解析雷達
│   ├── sniper.py            # 00:00 毫秒級極速搶票核心引擎 (已修復放票判定)
│   └── notifier.py          # 檔案 Log、控制台及 Telegram 通知模組
├── run_server.py            # SaaS Web 服務一鍵啟動腳本
├── cli.py                   # 單機 CLI 統一命令列入口
└── README.md
```

---

## 常用操作指令 (CLI)

### 1. 檢查 Session 有效性與時鐘校準
```cmd
python cli.py check
```
- 自動檢驗 `state.json` 是否有效，若過期會提示重新登入。
- 自動比對國家標準時間計算本機時鐘漂移量（Drift）。

### 2. 掃描特定日期與場地時段狀態
```cmd
python cli.py scan --court A --day 05
python cli.py scan --court B --day 05
```
- 掃描 05 日（週六）在 A 場與 B 場的所有時段狀態（已預約 / 09/01開放 / 可預約）。

### 3. 搶票全鏈路模擬推演 (Dry-Run)
```cmd
python cli.py dry-run --seconds 5
```
或直接執行專屬推演腳本：
```cmd
python tests/test_simulation.py
```

### 4. 正式 00:00 搶票守候任務 (推薦於 23:55 啟動)
```cmd
python cli.py snipe
```
- 會自動在 23:55 預熱進入系統並選擇網球場 A，精確在 `00:00:00.000`（補償本機時鐘偏差）瞬間發動極速預約。
- 首選命中 **網球場 A 17:00~18:00 及 18:00~19:00**。
- 若部分被搶，自動切換至網球場 B 或啟動全日曆撿漏備選。

---

## 關鍵技術特點

1. **毫秒級時間同步（Time Synchronization）**：
   - 透過 SNTP 直接查詢國家標準時間伺服器 (`time.stdtime.gov.tw`)，精確測出本機時間偏差（例如偏差 +1.058 秒），確保在絕對 00:00:00.000 觸發衝刺。
2. **PrimeFaces 雙場地 Section 精確定位**：
   - 區分 `#js-v1` (網球場 A) 與 `#js-v2` (網球場 B)，精確以時段前綴（`17:00~`、`18:00~`）鎖定目標，杜絕時段誤判。
3. **Session 預熱與 ViewState 保活**：
   - 提前進入頁面完成下拉選單選取，維持 PrimeFaces AJAX Session，避免 00:00 重新載入頁面造成的延遲與狀態遺失。
4. **極速對話框確認**：
   - 採用非阻塞等待與極速彈窗捕捉，單一時段點擊確認僅需 ~150-350ms。