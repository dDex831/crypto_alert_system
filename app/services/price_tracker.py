# 文件：app/services/price_tracker.py

import os
import logging
import sqlite3
from datetime import datetime, timedelta
import requests
import gspread
from app.models.database import init_db, save_price, DB_PATH
import json

# 初始化資料表（price_history）
init_db()

COINGECKO_URL = 'https://api.coingecko.com/api/v3/simple/price'

# Google Sheets 設定
# GOOGLE_SA_JSON: 環境變數裡的整段 service account JSON
# GOOGLE_SHEET_KEY: 試算表 ID
# GOOGLE_SHEET_WORKSHEET: 工作表名稱
GOOGLE_SA_JSON      = os.environ.get('GOOGLE_SA_JSON', '')
GS_SHEET_KEY        = os.environ.get('GOOGLE_SHEET_KEY', '')
GS_WORKSHEET_NAME   = os.environ.get('GOOGLE_SHEET_WORKSHEET', '')


def get_price(symbol: str) -> float:
    """
    取得指定幣種的 USD 價格
    """
    try:
        resp = requests.get(f"{COINGECKO_URL}?ids={symbol}&vs_currencies=usd", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[symbol]['usd']
    except Exception as e:
        logging.error(f"get_price 失敗 ({symbol}): {e}")
        raise


def purge_old_prices(days: int = 30):
    """
    刪除 price_history 中超過 days 天的舊資料
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM price_history WHERE timestamp < ?", (cutoff_str,))
        conn.commit()
        logging.info(f"已刪除 {cutoff_str} 之前的價格記錄")
    except Exception as e:
        logging.error(f"purge_old_prices 失敗: {e}")
    finally:
        conn.close()


def record_to_sheet(symbol: str, price: float):
    """
    當價格漲跌超過 ±5% 時，把記錄追加到 Google Sheet
    """
    if not GOOGLE_SA_JSON or not GS_SHEET_KEY or not GS_WORKSHEET_NAME:
        logging.warning("Google Sheet 設定不完整，跳過 record_to_sheet")
        return

    try:
        # 從環境變數解析憑證
        sa_info = json.loads(GOOGLE_SA_JSON)
        gc = gspread.service_account_from_dict(sa_info)

        sh = gc.open_by_key(GS_SHEET_KEY)
        ws = sh.worksheet(GS_WORKSHEET_NAME)

        rows = ws.get_all_values()
        if len(rows) > 1:
            last_price = float(rows[-1][2])  # 假設欄位: 時間, 幣種, 價格, 漲跌%
        else:
            last_price = price

        pct = (price - last_price) / last_price * 100 if last_price > 0 else 0
        if abs(pct) >= 5:
            now = datetime.now().isoformat(sep=' ')
            ws.append_row([now, symbol, price, f"{pct:+.2f}%"], value_input_option='USER_ENTERED')
            logging.info(f"已記錄到 Google Sheet: {symbol} {price} ({pct:+.2f}%)")
    except Exception as e:
        logging.error(f"record_to_sheet 失敗: {e}")


def check_and_save(symbol: str) -> float:
    """
    抓價格並寫入資料庫，同時保留最近一個月資料
    若漲跌 ±5%，則記錄到 Google Sheet
    回傳當下價格
    """
    price = get_price(symbol)
    save_price(symbol, price)
    record_to_sheet(symbol, price)
    purge_old_prices(days=30)
    logging.info(f"{symbol.upper()} 價格已寫入：{price}")
    return price


def list_price_history(limit: int = 100) -> list[dict]:
    """
    回傳最近的 price_history 紀錄
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT symbol, price, timestamp FROM price_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
    finally:
        conn.close()
    return [{'symbol': r[0], 'price': r[1], 'timestamp': r[2]} for r in rows]
