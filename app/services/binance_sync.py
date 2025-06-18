import logging
from datetime import datetime
from binance.client import Client
from app.models.database import init_db, save_trade

# 請確保以下環境變數或 config.json 已設定這些值
API_KEY = "geAphXbqepNS97LWVdB8FdkrdxStyCekEMtg4bsiq4IIFRqmrUj7OazZLpNAZvCU"
API_SECRET = "NZI7NGjZF749aSLY1h9NJRtOKYyX8a3zuhNPetCM1M2YLwP5FsVOnw2XAe0Zuxgf"
SYMBOL = "ADAUSDT"  # 可改成從 config.json 載入

def sync_trades():
    """從 Binance 抓取所有當前 symbol 的訂單，並存入 SQLite"""
    init_db()  # 確保表已建立
    client = Client(API_KEY, API_SECRET)
    try:
        orders = client.get_all_orders(symbol=SYMBOL)
    except Exception as e:
        logging.error(f"抓取 Binance 訂單失敗: {e}")
        return
    
    for o in orders:
        # o['time'] 是毫秒，要轉成 ISO 字串
        ts = datetime.fromtimestamp(o['time'] / 1000).isoformat(sep=' ')
        save_trade(
            o['symbol'],
            o['side'],
            float(o['price']),
            float(o['executedQty']),
            ts
        )

if __name__ == "__main__":
    logging.basicConfig(
        filename="binance_sync.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.info("Binance trade sync start")
    sync_trades()
    logging.info("Binance trade sync done")
