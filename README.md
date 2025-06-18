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
│   │   └── database.py       # SQLite 建表與查詢
├── frontend/
│   └── index.html            # Bootstrap + JS (多分頁切換)
├── config.json
├── run.py                    # 啟動 Flask
├── scheduler.py              # 定時執行邏輯
├── requirements.txt
├── Dockerfile
└── README.md
