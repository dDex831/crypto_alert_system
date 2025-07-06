# Crypto Alert System

## 網址:http://167.179.66.127/

## 簡介
Crypto Alert System 是一個自動化的加密貨幣監控與通知系統，主要功能包括：

- **價格追蹤與通知**：定時抓取多種幣種（例如 ADA、BTC）的最新價格，並依使用者設定的上下限進行停損/停利判斷，當價格觸發條件時透過 Email 發送提醒。
- **新聞擷取**：每日擷取區塊鏈與經濟相關主題的最高互動推文摘要，並管理快取以減少 API 呼叫。
- **Google Sheet 紀錄**：自動將每次價格與新聞的結果寫入 Google Sheet，便於後續分析與查閱。
- **前端控制面板**：`frontend/index.html` 提供靜態網頁，可手動觸發任務與查看最新狀態。
- **Docker 支援**：內建 Dockerfile，一鍵建構容器映像並執行。

## 功能總覽
1. **價格監控**：
   - 每小時取得指定幣種最新價格
   - 自動判斷上下限並通知
2. **新聞彙整**：
   - 單次呼叫 Twitter API 同步擷取區塊鏈與經濟主題推文
   - 過濾昨日發布並選出最高互動
3. **紀錄保存**：
   - 價格與新聞結果同步寫入 SQLite 與 Google Sheet
4. **排程執行**：
   - `scheduler.py` 設定任務排程（可搭配系統排程或服務管理器運行）
5. **控制面板**：
   - 前端控制面板（React + PWA）

## 專案結構
```text
crypto_alert_system/
├─ app/
│   ├─ __init__.py        # 套件初始化
│   ├─ api.py             # REST API 入口
│   ├─ services/          # 幣價、新聞、Email、Google Sheet 模組
│   └─ models/            # SQLite 資料模型
├─ frontend/
│   ├─ public/
│   │   ├─ index.html
│   │   ├─ manifest.json
│   │   ├─ favicon.ico
│   │   └─ ...
│   └─ src/
│       ├─ App.js
│       └─ ...
├── monitoring/
│   └── prometheus.yml
├─ config.json            # 系統配置檔
├─ run.py                 # 主流程啟動腳本
├─ scheduler.py           # 任務排程腳本
├─ requirements.txt       # Python 相依套件列表
├─ Dockerfile             # Docker 映像建構設定
└─ README.md              # 專案說明
```




## 前端控制面板（React + PWA）
新版前端控制面板以 React 重新開發，支援多頁切換與 PWA (Progressive Web App) 離線安裝，
提供即時行情、交易紀錄、新聞摘要與筆記管理等功能，介面現代化且可直接安裝到手機桌面。

特色
多頁式 UI（價格設定、交易紀錄、新聞摘要、筆記管理）

即時 API 串接 Flask 後端

PWA 支援：可離線瀏覽、支援桌面/手機安裝

Bootstrap 5 樣式，響應式設計


瀏覽 http://localhost:3000
頁面自動 proxy API 請求到 Flask (http://localhost:5000)

```text
frontend/
├─ public/
│   ├─ index.html
│   ├─ manifest.json
│   └─ ...
└─ src/
    ├─ App.js
    ├─ pages/
    │   ├─ PricePage.js
    │   ├─ TradesPage.js
    │   ├─ NewsPage.js
    │   └─ ToolsPage.js
    └─ ...
```
啟動 Flask 後端於 5000 端口：
python run.py
另開新終端機，啟動 React 前端（於 frontend 目錄）：

cd frontend
npm install   # 僅第一次需安裝相依套件
npm start

