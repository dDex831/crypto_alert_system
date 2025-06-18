crypto_alert_system/
├── app/
│   ├── __init__.py
│   ├── api.py                # Flask API 路由
│   ├── services/
│   │   ├── price_tracker.py  # 幣價邏輯
│   │   ├── news_fetcher.py   # 抓區塊鏈新聞
│   │   ├── email_alert.py    # Email 通知模組
│   │   ├── google_sheet.py   # Google Sheet 操作
│   ├── models/
│       └── database.py       # SQLite 建表與查詢
│       └── price_history.db   
│ 
├── frontend/
│   └── index.html            # Bootstrap + JS (多分頁切換)
├── config.json
├── run.py                    # 啟動 Flask
├── scheduler.py              # 定時執行邏輯
├── requirements.txt
├── Dockerfile
└── README.md

price_history.db

-- 建立幣價歷史紀錄表格
CREATE TABLE price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 唯一識別編號，自動遞增
  symbol TEXT NOT NULL,                   -- 幣種名稱，例如 'ADA', 'BTC'
  price REAL NOT NULL,                    -- 當下的價格（浮點數格式）
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP -- 資料寫入時間，自動填入目前時間
);

