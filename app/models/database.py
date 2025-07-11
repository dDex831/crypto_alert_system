import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# ---- 路徑設定 ----
# 新資料庫位置：使用者家目錄下的隱藏資料夾
DATA_DIR = Path.home() / ".crypto_alert_system"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = str(DATA_DIR / "price_history.db")

# 舊的資料庫（遺留在原程式碼目錄下）
OLD_DB_PATH = Path(__file__).parent / "price_history.db"


def init_db():
    """
    1) 在新路徑建立資料夾和資料庫
    2) 建立三張表（trade_history、notes、price_history）
    3) 如果找到舊 DB，就把 notes 表的資料搬過來
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

    # 建立價格歷史表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol    TEXT    NOT NULL,
        price     REAL    NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

    # 如果舊資料庫存在，就附加並把 notes 資料搬過來
    if OLD_DB_PATH.exists():
        try:
            conn.execute("ATTACH DATABASE ? AS old_db", (str(OLD_DB_PATH),))
            conn.execute("""
            INSERT OR IGNORE INTO notes (
              id, title, code, explanation, purpose, result, created_at, updated_at
            )
            SELECT
              id, title, code, explanation, purpose, result, created_at, updated_at
            FROM old_db.notes
            """)
            conn.commit()
            logging.info(f"Migrated notes from {OLD_DB_PATH}")
        except sqlite3.DatabaseError as e:
            logging.error(f"[DB Migration] 無法從舊 DB 搬移資料: {e}")
        finally:
            conn.execute("DETACH DATABASE old_db")

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
          trade["id"],
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
    cursor.execute(
        "INSERT INTO price_history (symbol, price) VALUES (?, ?)",
        (symbol, price)
    )
    conn.commit()
    conn.close()
    logging.info(f"{symbol} saved at {price}")
