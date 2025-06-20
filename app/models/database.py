import sqlite3, os, logging
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "price_history.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 如果表还没改过，就先建一份包含 trade_id 的表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_history (
      id             INTEGER PRIMARY KEY AUTOINCREMENT,
      trade_id       INTEGER NOT NULL,    -- Binance 的 tradeId
      order_id       INTEGER NOT NULL,
      symbol         TEXT    NOT NULL,
      side           TEXT    NOT NULL,
      price          REAL    NOT NULL,
      quantity       REAL    NOT NULL,
      commission     REAL    NOT NULL,
      commission_asset TEXT  NOT NULL,
      quote_qty      REAL    NOT NULL,
      is_maker       INTEGER NOT NULL,
      trade_time     DATETIME NOT NULL,
      UNIQUE(trade_id)             -- 保证同一个执行只插入一次
    )
    """)
    conn.commit()
    conn.close()

def save_trade(trade: dict):
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    try:
        c.execute("""
          INSERT INTO trade_history
            (trade_id, order_id, symbol, side, price, quantity,
             commission, commission_asset, quote_qty, is_maker, trade_time)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
          trade["id"],                # Binance 回传的 tradeId
          trade["orderId"],
          trade["symbol"],
          "BUY" if trade["isBuyer"] else "SELL",
          float(trade["price"]),
          float(trade["qty"]),
          float(trade["commission"]),
          trade["commissionAsset"],
          float(trade["quoteQty"]),
          1 if trade["isMaker"] else 0,
          datetime.fromtimestamp(trade["time"]/1000).isoformat(sep=' ')
        ))
    except sqlite3.IntegrityError:
        # 已经有这笔 trade_id 了，就跳过
        pass
    conn.commit()
    conn.close()

def save_price(symbol: str, price: float):
    """写入一笔币价历史记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
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