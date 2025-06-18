import schedule
import time
from app.services.binance_sync import sync_trades

# 啟動時先執行一次同步
sync_trades()

# 每5分鐘同步一次交易紀錄
schedule.every(5).minutes.do(sync_trades)

if __name__ == "__main__":
    print("Scheduler started: syncing every 5 minutes...")
    while True:
        schedule.run_pending()
        time.sleep(1)
