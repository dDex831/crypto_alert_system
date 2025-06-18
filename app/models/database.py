import sqlite3
import os
import logging

DB_PATH = os.path.join(os.path.dirname(__file__), "price_history.db")

def init_db():
    """初始化所有資料表（如不存在就建立）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 幣價歷史紀錄
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 交易歷史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,         -- 交易對（如 ADAUSDT）
            side TEXT NOT NULL,           -- 買/賣 (`BUY` or `SELL`)
            price REAL NOT NULL,          -- 下單價格
            quantity REAL NOT NULL,       -- 執行數量
            trade_time DATETIME NOT NULL  -- 交易時間
        )
    """)
    conn.commit()
    conn.close()

def save_price(symbol: str, price: float):
    """寫入一筆幣價資料"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO price_history (symbol, price) VALUES (?, ?)",
        (symbol, price)
    )
    conn.commit()
    conn.close()
    logging.info(f"{symbol} price saved: {price}")

def save_trade(symbol: str, side: str, price: float, quantity: float, trade_time: str):
    """寫入一筆 Binance 交易紀錄"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO trade_history (symbol, side, price, quantity, trade_time)
           VALUES (?, ?, ?, ?, ?)""",
        (symbol, side, price, quantity, trade_time)
    )
    conn.commit()
    conn.close()
    logging.info(f"Trade saved: {symbol} {side} {quantity}@{price} at {trade_time}")
