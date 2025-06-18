import requests
import smtplib
import logging
import schedule
import time
import os
import json
import sqlite3
from datetime import datetime
from email.mime.text import MIMEText
from app.models.database import save_price, init_db

# 取得專案根目錄（往上兩層）
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# === 載入設定 ===
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

SYMBOL = config['symbol']
THRESHOLD_HIGH = config['threshold_high']
THRESHOLD_LOW = config['threshold_low']

EMAIL_SENDER = config['email']['sender']
EMAIL_RECEIVER = config['email']['receiver']
EMAIL_PASSWORD = config['email']['password']

# === 日誌設定 ===
logging.basicConfig(
    filename='alert.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# === 幣價抓取 ===
def get_price(symbol):
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data[symbol]['usd']
    except Exception as e:
        logging.error(f'抓取價格失敗: {e}')
        return None

# === 發送 Email ===
def send_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        logging.info(f"Email 已發送: {subject}")
    except Exception as e:
        logging.error(f"發送 Email 失敗: {e}")
        print(f"[錯誤] 發送 Email 失敗: {e}")

# === 價格檢查主邏輯 ===
def check_price():
    price = get_price(SYMBOL)
    if price is None:
        return

    logging.info(f'{SYMBOL.upper()} 價格: ${price:.4f}')
    save_price(SYMBOL, price)  # ✅ 寫入 SQLite
    
    if price > THRESHOLD_HIGH:
        send_email(
            f'{SYMBOL.upper()} 價格高於 {THRESHOLD_HIGH}',
            f'目前價格為 ${price:.4f}，請注意可能逢高。'
        )
    elif price < THRESHOLD_LOW:
        send_email(
            f'{SYMBOL.upper()} 價格低於 {THRESHOLD_LOW}',
            f'目前價格為 ${price:.4f}，可考慮加倉。'
        )

# === 每10分鐘執行一次 ===
schedule.every(10).minutes.do(check_price)

if __name__ == "__main__":
    
    logging.info("自動追蹤系統啟動")
    init_db()
    check_price()
    while True:
        schedule.run_pending()
        time.sleep(10)
