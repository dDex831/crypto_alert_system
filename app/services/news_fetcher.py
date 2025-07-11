import os
import logging
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import requests
from dotenv import load_dotenv

# 載入 .env 裡的環境變數
load_dotenv()

# ----- CryptoCompare Public API 設定 -----
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "")
CRYPTOCOMPARE_URL = "https://min-api.cryptocompare.com/data/v2/news/"
CC_HEADERS = {"authorization": f"Apikey {CRYPTOCOMPARE_KEY}"} if CRYPTOCOMPARE_KEY else {}

# ----- 快取檔路徑 -----
CACHE_FILE = Path(__file__).parent / ".news_cache.json"


def _load_cache() -> Dict[str, Any]:
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
    payload = {
        "_ts": time.time(),
        "blockchain": blockchain,
        "economy": economy
    }
    CACHE_FILE.write_text(json.dumps(payload))


def _filter_latest(articles: List[Dict]) -> List[Dict]:
    """過濾過去 24 小時最新文章"""
    if not articles:
        return []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    valid = [
        a for a in articles
        if datetime.utcfromtimestamp(a.get("published_on", 0)) >= cutoff
    ]
    top = max(valid or articles, key=lambda x: x.get("published_on", 0))
    return [{
        "title": top.get("title"),
        "url": top.get("url"),
        "image": top.get("imageurl"),
        "source": top.get("source_info", {}).get("name", "CryptoCompare")
    }]


def _search_cryptocompare(category: str) -> List[Dict]:
    if not CRYPTOCOMPARE_KEY:
        logging.warning(f"CryptoCompare API Key 未設定，跳過 {category} 搜尋")
        return []
    params = {"categories": category.upper(), "lang": "EN"}
    try:
        resp = requests.get(CRYPTOCOMPARE_URL, headers=CC_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        articles = resp.json().get("Data", [])
        return _filter_latest(articles)
    except Exception as e:
        logging.error(f"CryptoCompare API ({category}) 失敗: {e}")
        return []


def fetch_top_blockchain_news() -> List[Dict]:
    return _search_cryptocompare("ADA")  # 可改為 Blockchain


def fetch_top_economy_news() -> List[Dict]:
    return _search_cryptocompare("Business")  # 模擬經濟新聞類別


def fetch_daily_news() -> Dict[str, List[Dict]]:
    cache = _load_cache()
    bc = cache.get("blockchain") or fetch_top_blockchain_news()
    ec = cache.get("economy") or fetch_top_economy_news()
    if not cache:
        _save_cache(bc, ec)
    return {"blockchain": bc, "economy": ec}
