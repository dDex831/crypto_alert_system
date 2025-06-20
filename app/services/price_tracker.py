# 文件：app/services/price_tracker.py

import requests
import logging
from app.models.database import init_db, save_price

# 先初始化資料表（price_history）
init_db()

COINGECKO_URL = 'https://api.coingecko.com/api/v3/simple/price'

def get_price(symbol: str) -> float:
    """
    取得指定幣種的 USD 價格
    symbol: CoinGecko 上的 id，例如 'cardano', 'bitcoin'
    回傳 float 價格，失敗時丟出例外
    """
    try:
        resp = requests.get(
            f"{COINGECKO_URL}?ids={symbol}&vs_currencies=usd",
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return data[symbol]['usd']
    except Exception as e:
        logging.error(f"get_price 失敗 ({symbol}): {e}")
        raise

def check_and_save(symbol: str) -> float:
    """
    抓價格並寫入資料庫
    回傳當下價格
    """
    price = get_price(symbol)
    save_price(symbol, price)
    logging.info(f"{symbol.upper()} 價格已寫入：{price}")
    return price

def list_price_history(limit: int = 100) -> list[dict]:
    """
    回傳最近的 price_history 紀錄
    limit: 最多筆數，預設 100
    回傳格式：[{ 'symbol': ..., 'price': ..., 'timestamp': ... }, …]
    """
    import sqlite3
    from os.path import dirname, join

    db = join(dirname(dirname(__file__)), 'models', 'price_history.db')
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT symbol, price, timestamp "
        "FROM price_history "
        "ORDER BY id DESC "
        "LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {'symbol': r[0], 'price': r[1], 'timestamp': r[2]}
        for r in rows
    ]
