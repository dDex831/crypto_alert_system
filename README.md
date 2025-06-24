# Crypto Alert System

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
   - 靜態 HTML，可透過簡易 HTTP 伺服器提供本地查看

## 環境需求
- Python 3.8 以上
- SQLite（內建，不需額外安裝）
- Docker（選用）
- 其他依賴請見 `requirements.txt`

## 快速上手
1. **Clone 專案**
   ```bash
   git clone https://github.com/dDex831/crypto_alert_system.git
   cd crypto_alert_system
   ```
2. **安裝套件**
   ```bash
   pip install -r requirements.txt
   ```
3. **建立並編輯 `config.json`**（範例）
   ```json
   {
     "alert": {
       "symbols": ["ADA", "BTC"],
       "thresholds": {
         "ADA": {"min": 0.8, "max": 1.2},
         "BTC": {"min": 30000, "max": 60000}
       },
       "email": {
         "smtp_server": "smtp.example.com",
         "smtp_port": 587,
         "username": "your_email@example.com",
         "password": "your_email_password",
         "recipients": ["alert1@example.com", "alert2@example.com"]
       }
     },
     "google_sheet": {
       "spreadsheet_id": "YOUR_SPREADSHEET_ID",
       "credentials_file": "credentials.json"
     },
     "schedule": {
       "price_interval_hours": 1,
       "news_time": "08:00"
     }
   }
   ```
4. **執行主流程**
   ```bash
   python run.py
   ```
5. **使用排程腳本**
   ```bash
   python scheduler.py
   ```
6. **啟動前端面板**
   ```bash
   cd frontend
   python -m http.server 8000
   ```

## 專案結構
```text
crypto_alert_system/
├─ app/
│   ├─ __init__.py        # 套件初始化
│   ├─ api.py             # REST API 入口
│   ├─ services/          # 幣價、新聞、Email、Google Sheet 模組
│   └─ models/            # SQLite 資料模型
├─ frontend/
│   └─ index.html         # 控制面板靜態頁面
├─ config.json            # 系統配置檔
├─ run.py                 # 主流程啟動腳本
├─ scheduler.py           # 任務排程腳本
├─ requirements.txt       # Python 相依套件列表
├─ Dockerfile             # Docker 映像建構設定
└─ README.md              # 專案說明
```

## Docker 使用
1. **建構映像**
   ```bash
   docker build -t crypto-alert .
   ```
2. **執行容器**
   ```bash
   docker run -d \
     -v $(pwd)/config.json:/app/config.json \
     -v $(pwd)/credentials.json:/app/credentials.json \
     crypto-alert
   ```

## 授權 License
本專案採用 MIT License，詳見 LICENSE 檔案。
