# 文件：app/services/news_fetcher.py
"""
新聞擷取模組（Twitter + 快取 + 圖片 + 每日清除）
提供：
 - fetch_top_blockchain_news(): 回傳區塊鏈主題最高互動文章（一筆）
 - fetch_top_economy_news(): 回傳純經濟相關最高互動文章（一筆）
 - fetch_daily_news(): 同時回傳兩類每日摘要，並管理快取與每日清除
"""
import os
import logging
import json
import time
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Any
from pathlib import Path
from urllib.parse import unquote
import requests
from dotenv import load_dotenv

load_dotenv()

# Twitter API 設定
raw_token = os.getenv("TWITTER_BEARER_TOKEN", "")
BEARER_TOKEN = unquote(raw_token)
HEADERS = {"Authorization": f"Bearer {BEARER_TOKEN}"} if BEARER_TOKEN else {}
TW_API_URL = "https://api.twitter.com/2/tweets/search/recent"
MAX_RESULTS = 10

# 查詢參數
BLOCKCHAIN_QUERY = "blockchain OR crypto"
ECONOMY_QUERY   = "(economy OR inflation OR fed) -blockchain -crypto"

# 快取檔
CACHE_FILE = Path(__file__).parent / ".news_cache.json"

# Twitter API call base parameters
TW_PARAMS_BASE = {
    "max_results": MAX_RESULTS,
    "tweet.fields": "public_metrics,created_at,attachments",
    "expansions": "attachments.media_keys",
    "media.fields": "url"
}


def _load_cache() -> Dict[str, Any]:
    """
    讀取快取，並於每日 8:00 過後清除昨日快取
    """
    if not CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text())
    except Exception:
        logging.warning("快取檔讀取失敗，將重新抓取")
        return {}

    # 刪除昨日快取：若已過今日08:00且為昨日資料，則視為失效
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
    """將最新文章寫入快取，附上時間戳"""
    CACHE_FILE.write_text(json.dumps({
        "_ts": time.time(),
        "blockchain": blockchain,
        "economy":   economy
    }))


def _search_twitter(query: str) -> Tuple[List[Dict], Dict[str, str]]:
    """呼叫 Twitter API，失敗或限流時回空"""
    if not BEARER_TOKEN:
        logging.warning("TWITTER_BEARER_TOKEN 未設定，跳過 Twitter 搜尋")
        return [], {}
    try:
        resp = requests.get(
            TW_API_URL,
            headers=HEADERS,
            params={**TW_PARAMS_BASE, "query": query},
            timeout=10
        )
        resp.raise_for_status()
        j = resp.json()
        tweets = j.get("data", [])
        includes = j.get("includes", {})
        media_map = { m.get("media_key"): m.get("url") for m in includes.get("media", []) }
        return tweets, media_map
    except requests.exceptions.RequestException as e:
        logging.error(f"Twitter API ({query}) 失敗: {e}")
        return [], {}


def _top_one_with_media(raw: List[Dict], media_map: Dict[str, str]) -> List[Dict]:
    """取得最高互動推文，回傳完整文字、連結、圖片"""
    if not raw:
        return []
    t = sorted(
        raw,
        key=lambda x: x.get("public_metrics", {}).get("like_count", 0)
                  + x.get("public_metrics", {}).get("retweet_count", 0),
        reverse=True
    )[0]
    img = None
    for mk in t.get("attachments", {}).get("media_keys", []):
        if mk in media_map:
            img = media_map[mk]
            break
    return [{
        "title": t.get("text", ""),
        "url":   f"https://twitter.com/i/web/status/{t.get('id')}",
        "image": img
    }]

def fetch_top_blockchain_news() -> List[Dict]:
    """
    回傳昨天發布之區塊鏈主題最高互動文章（一筆）
    """
    raw, media_map = _search_twitter(BLOCKCHAIN_QUERY)
    # 計算昨天日期
    yesterday = date.today() - timedelta(days=1)
    # 過濾出 created_at 屬性等於昨天的推文
    filtered = []
    for t in raw:
        try:
            # Twitter 回傳的 created_at 範例: "2025-06-19T14:23:00.000Z"
            dt = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            if dt.date() == yesterday:
                filtered.append(t)
        except Exception:
            continue
    # 如果昨天沒資料，就保留所有 raw
    if not filtered:
        filtered = raw
    return _top_one_with_media(filtered, media_map)

def fetch_top_economy_news() -> List[Dict]:
    """
    回傳昨天發布之純經濟相關最高互動文章（一筆）
    """
    raw, media_map = _search_twitter(ECONOMY_QUERY)
    yesterday = date.today() - timedelta(days=1)
    filtered = []
    for t in raw:
        try:
            dt = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            if dt.date() == yesterday:
                filtered.append(t)
        except Exception:
            continue
    if not filtered:
        filtered = raw
    return _top_one_with_media(filtered, media_map)


def fetch_daily_news() -> Dict[str, List[Dict]]:
    """
    主流程：
    1. 嘗試讀取快取
    2. 若兩種文章都已有快取，直接回傳
    3. 否則僅對缺失的類別呼叫 API，保留已有快取
    4. 用新結果覆寫快取
    """
    cache = _load_cache()
    bc_cached = cache.get("blockchain", [])
    ec_cached = cache.get("economy", [])

    # 若兩類都有快取且非空，直接回傳
    if bc_cached and ec_cached:
        return {"blockchain": bc_cached, "economy": ec_cached}

    # 僅對缺失一方呼叫 API
    bc = bc_cached or fetch_top_blockchain_news()
    ec = ec_cached or fetch_top_economy_news()

    # API 呼叫後立即覆寫快取
    _save_cache(bc, ec)
    return {"blockchain": bc, "economy": ec}
