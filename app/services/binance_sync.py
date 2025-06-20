import logging, os
from datetime import datetime
from binance.client import Client
from dotenv import load_dotenv
from app.models.database import init_db, save_trade

load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY","").strip()
API_SECRET = os.getenv("BINANCE_API_SECRET","").strip()
SYMBOL = "ADAUSDT"

def sync_trades():
    init_db()
    if not (API_KEY and API_SECRET):
        logging.error("缺少 Binance API Key/Secret！")
        return
    client = Client(API_KEY, API_SECRET)
    try:
        trades = client.get_my_trades(symbol=SYMBOL)
    except Exception as e:
        logging.error(f"抓取 Binance 交易執行檔失敗: {e}")
        return

    for t in trades:
        save_trade(t)
