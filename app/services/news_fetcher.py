# 文件：app/services/news_fetcher.py
"""
新聞擷取模組（Twitter + 快取 + 圖片）
提供：
 - fetch_top_blockchain_news(): 回傳區塊鏈主題最高互動文章（一筆）
 - fetch_top_economy_news(): 回傳經濟主題最高互動文章（一筆）
 - fetch_daily_news(): 同時回傳兩類每日摘要
"""
import os
import logging
import json
import time
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
# 排除 blockchain/crypto，確保只抓純經濟相關
ECONOMY_QUERY = "(economy OR inflation OR fed) -blockchain -crypto"

# 快取檔與 TTL（一天）
CACHE_FILE = Path(__file__).parent / ".news_cache.json"
CACHE_TTL = 60  # 24 小時

# Twitter API call parameters base
TW_PARAMS_BASE = {
    "max_results": MAX_RESULTS,
    "tweet.fields": "public_metrics,created_at,attachments",
    "expansions": "attachments.media_keys",
    "media.fields": "url"
}


def _load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            if time.time() - data.get("_ts", 0) < CACHE_TTL:
                return data
        except Exception:
            logging.warning("快取檔讀取失敗，將重新抓取")
    return {}


def _save_cache(blockchain: List[Dict], economy: List[Dict]):
    CACHE_FILE.write_text(json.dumps({
        "_ts": time.time(),
        "blockchain": blockchain,
        "economy": economy
    }))


def _search_twitter(query: str) -> Tuple[List[Dict], Dict[str, str]]:
    """呼叫 Twitter API，失敗或限流時回空列表"""
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
        media_items = includes.get("media", [])
        media_map = { m.get("media_key"): m.get("url") for m in media_items }
        return tweets, media_map
    except requests.exceptions.RequestException as e:
        logging.error(f"Twitter API ({query}) 失敗: {e}")
        return [], {}


def _top_one_with_media(raw: List[Dict], media_map: Dict[str, str]) -> List[Dict]:
    """從原始列表取最高互動一筆，附帶可能的圖片"""
    if not raw:
        return []
    sorted_list = sorted(
        raw,
        key=lambda x: x.get("public_metrics", {}).get("like_count", 0)
                  + x.get("public_metrics", {}).get("retweet_count", 0),
        reverse=True
    )
    t = sorted_list[0]
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
    raw, media_map = _search_twitter(BLOCKCHAIN_QUERY)
    return _top_one_with_media(raw, media_map)


def fetch_top_economy_news() -> List[Dict]:
    raw, media_map = _search_twitter(ECONOMY_QUERY)
    if raw:
        return _top_one_with_media(raw, media_map)
    # 开发阶段示例
    return [{
      "title": "【示例經濟文章】Fed keeps rates unchanged, inflation cools…",
      "url":   "",
      "image": None
    }]



def fetch_daily_news() -> Dict[str, List[Dict]]:
    """
    回傳當日新聞摘要，使用快取保護：
    1. 若快取存在且至少有一篇，直接回傳快取
    2. 否則嘗試拉取並在成功時更新快取
    """
    cache = _load_cache()
    if cache and (cache.get("blockchain") or cache.get("economy")):
        return {"blockchain": cache.get("blockchain", []),
                "economy":   cache.get("economy", [])}
    bc = fetch_top_blockchain_news()
    ec = fetch_top_economy_news()
    if bc or ec:
        _save_cache(bc, ec)
    return {"blockchain": bc, "economy": ec}
