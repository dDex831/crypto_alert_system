import os  # 存取環境變數與檔案系統
import logging  # 日誌紀錄
import json  # JSON 編碼與解碼
import time  # 處理時間戳記
from datetime import datetime  # 日期時間操作
from typing import List, Dict, Any  # 型別註解
from pathlib import Path  # 處理檔案路徑
import requests  # HTTP 請求
from dotenv import load_dotenv  # 讀取 .env

load_dotenv()  # 載入環境變數

# ----- CryptoCompare Public API 設定 -----
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "")
CRYPTOCOMPARE_URL = "https://min-api.cryptocompare.com/data/v2/news/"
CC_HEADERS = {"authorization": f"Apikey {CRYPTOCOMPARE_KEY}"} if CRYPTOCOMPARE_KEY else {}

# ----- NewsAPI.org 設定 -----
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"

# ----- 快取檔路徑 -----
CACHE_FILE = Path(__file__).parent / ".news_cache.json"


def _load_cache() -> Dict[str, Any]:
    """
    讀取並驗證快取，若今日08:00後快取屬昨日即清除
    """
    if not CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text())
    except Exception:
        logging.warning("快取讀取失敗，將重新抓取")
        return {}

    ts = data.get("_ts", 0)
    cache_dt = datetime.fromtimestamp(ts)
    now = datetime.now()
    if now.hour >= 8 and cache_dt.date() < now.date():
        try:
            CACHE_FILE.unlink()
        except Exception:
            pass
        return {}
    return data


def _save_cache(blockchain: List[Dict], economy: List[Dict]):
    """保存最新兩主題文章至快取並附時間戳"""
    CACHE_FILE.write_text(json.dumps({
        "_ts": time.time(),
        "blockchain": blockchain,
        "economy": economy
    }))


def _search_cryptocompare() -> List[Dict]:
    """
    使用 CryptoCompare Public API 抓取 Cardano (ADA) 相關新聞
    """
    if not CRYPTOCOMPARE_KEY:
        logging.warning("CRYPTOCOMPARE_API_KEY 未設定，跳過區塊鏈新聞搜尋")
        return []
    params = {
        "categories": "ADA",
        "lang": "EN"
    }
    try:
        resp = requests.get(CRYPTOCOMPARE_URL, headers=CC_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("Data", [])
        if not articles:
            return []
        # 依 published_on (Unix timestamp) 選取最新一筆
        top = sorted(articles, key=lambda x: x.get("published_on", 0), reverse=True)[0]
        source = top.get("source_info", {}).get("name", "CryptoCompare")
        return [{
            "title": top.get("title"),
            "url": top.get("url"),
            "image": top.get("imageurl"),
            "source": source
        }]
    except requests.exceptions.RequestException as e:
        logging.error(f"CryptoCompare API 失敗: {e}")
        return []


def _search_newsapi_economy() -> List[Dict]:
    """
    使用 NewsAPI.org 抓取純經濟相關新聞
    """
    if not NEWSAPI_KEY:
        logging.warning("NEWSAPI_KEY 未設定，跳過經濟新聞搜尋")
        return []
    params = {
        "apiKey": NEWSAPI_KEY,
        "category": "business",
        "q": "economy",
        "pageSize": 1,
        "language": "en"
    }
    try:
        resp = requests.get(NEWSAPI_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        if not articles:
            return []
        a = articles[0]
        return [{
            "title": a.get("title"),
            "url": a.get("url"),
            "image": a.get("urlToImage"),
            "source": a.get("source", {}).get("name", "NewsAPI")
        }]
    except requests.exceptions.RequestException as e:
        logging.error(f"NewsAPI.org 經濟新聞 API 失敗: {e}")
        return []


def fetch_top_blockchain_news() -> List[Dict]:
    """回傳 Cardano 主題最新文章（一筆）"""
    return _search_cryptocompare()


def fetch_top_economy_news() -> List[Dict]:
    """回傳純經濟相關最高互動文章（一筆）"""
    return _search_newsapi_economy()


def fetch_daily_news() -> Dict[str, List[Dict]]:
    """主流程：同時取得 Cardano 與經濟新聞，並管理快取與每日清除"""
    cache = _load_cache()
    bc_cached = cache.get("blockchain", [])
    ec_cached = cache.get("economy", [])
    if bc_cached and ec_cached:
        return {"blockchain": bc_cached, "economy": ec_cached}

    bc = bc_cached or _search_cryptocompare()
    ec = ec_cached or _search_newsapi_economy()
    _save_cache(bc, ec)
    return {"blockchain": bc, "economy": ec}
