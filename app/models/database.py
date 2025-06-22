import sqlite3
import os
import logging
from datetime import datetime

# 資料庫路徑
DB_PATH = os.path.join(os.path.dirname(__file__), "price_history.db")


def init_db():
    """
    初始化資料庫結構:
    - trade_history: Binance 交易執行紀錄
    - notes: 程式筆記 CRUD
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 建立交易歷史表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_history (
      id               INTEGER PRIMARY KEY AUTOINCREMENT,
      trade_id         INTEGER NOT NULL,
      order_id         INTEGER NOT NULL,
      symbol           TEXT    NOT NULL,
      side             TEXT    NOT NULL,
      price            REAL    NOT NULL,
      quantity         REAL    NOT NULL,
      commission       REAL    NOT NULL,
      commission_asset TEXT    NOT NULL,
      quote_qty        REAL    NOT NULL,
      is_maker         INTEGER NOT NULL,
      trade_time       DATETIME NOT NULL,
      UNIQUE(trade_id)
    )
    """)

    # 建立程式筆記表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      title       TEXT    NOT NULL,
      code        TEXT    NOT NULL,
      explanation TEXT,
      purpose     TEXT,
      result      TEXT,
      created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_trade(trade: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
          INSERT INTO trade_history (
            trade_id, order_id, symbol, side,
            price, quantity, commission,
            commission_asset, quote_qty,
            is_maker, trade_time
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
          trade["id"],                   # Binance tradeId
          trade["orderId"],
          trade["symbol"],
          "BUY" if trade.get("isBuyer") else "SELL",
          float(trade.get("price", 0)),
          float(trade.get("qty", 0)),
          float(trade.get("commission", 0)),
          trade.get("commissionAsset", ""),
          float(trade.get("quoteQty", 0)),
          1 if trade.get("isMaker") else 0,
          datetime.fromtimestamp(trade.get("time", 0)/1000).isoformat(sep=' ')
        ))
    except sqlite3.IntegrityError:
        pass
    conn.commit()
    conn.close()


def save_price(symbol: str, price: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol    TEXT    NOT NULL,
            price     REAL    NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "INSERT INTO price_history (symbol, price) VALUES (?, ?)",
        (symbol, price)
    )
    conn.commit()
    conn.close()
    logging.info(f"{symbol} saved at {price}")
