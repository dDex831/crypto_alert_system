## 專案結構

```text
crypto_alert_system/
├─ app/
│   ├─ __init__.py
│   ├─ api.py
│   ├─ services/     # 幣價、新聞、Email、Google Sheet
│   └─ models/       # SQLite 資料庫
├─ frontend/         # 控制台靜態頁面
├─ config.json
├─ run.py
├─ scheduler.py
├─ requirements.txt
├─ Dockerfile
└─ README.md


price_history.db

-- 建立幣價歷史紀錄表格
CREATE TABLE price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 唯一識別編號，自動遞增
  symbol TEXT NOT NULL,                   -- 幣種名稱，例如 'ADA', 'BTC'
  price REAL NOT NULL,                    -- 當下的價格（浮點數格式）
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP -- 資料寫入時間，自動填入目前時間
);

