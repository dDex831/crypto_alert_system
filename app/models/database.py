import sqlite3
import os

# 資料庫路徑（相對於專案根目錄）
DB_PATH = os.path.join(os.path.dirname(__file__), "price_history.db")

def init_db():
    """初始化資料庫（若尚未建表則建立）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 唯一識別編號
            symbol TEXT NOT NULL,                  -- 幣種代號（如 'ADA', 'BTC'）
            price REAL NOT NULL,                   -- 當下價格
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP  -- 自動填入時間
        )
    """)
    conn.commit()
    conn.close()

def save_price(symbol: str, price: float):
    """寫入一筆幣價資料"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO price_history (symbol, price)
        VALUES (?, ?)
    """, (symbol, price))
    conn.commit()
    conn.close()
