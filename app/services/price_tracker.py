# 文件：app/services/news_fetcher.py
"""
新聞擷取模組
提供：
 - fetch_top_blockchain_news(): 回傳區塊鏈主題最高互動文章清單
 - fetch_top_economy_news(): 回傳經濟主題最高互動文章清單
 - fetch_daily_news(): 同時回傳兩類每日摘要
"""
from typing import List, Dict

# TODO: 使用 Twitter API v2 或 News API 實作

# 範例使用 Twitter API v2，需先申請 Bearer Token
BEARER_TOKEN = "YOUR_TWITTER_BEARER_TOKEN"
import requests

SEARCH_HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

# 查詢參數，可依需求調整
BLOCKCHAIN_QUERY = "blockchain OR crypto"
ECONOMY_QUERY = "economy OR inflation OR fed"
MAX_RESULTS = 10


def fetch_top_blockchain_news() -> List[Dict]:
    """回傳 list[{'title': str, 'url': str}]"""
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        'query': BLOCKCHAIN_QUERY,
        'max_results': MAX_RESULTS,
        'tweet.fields': 'public_metrics,created_at'
    }
    resp = requests.get(url, headers=SEARCH_HEADERS, params=params)
    resp.raise_for_status()
    data = resp.json().get('data', [])
    # 依互動數排序 (likes + retweets)
    sorted_list = sorted(
        data,
        key=lambda x: x['public_metrics']['like_count'] + x['public_metrics']['retweet_count'],
        reverse=True
    )
    top = sorted_list[:1]
    return [{
        'title': t['text'][:50] + '...',  # 取前50字
        'url': f"https://twitter.com/i/web/status/{t['id']}"
    } for t in top]


def fetch_top_economy_news() -> List[Dict]:
    """回傳 list[{'title': str, 'url': str}]"""
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        'query': ECONOMY_QUERY,
        'max_results': MAX_RESULTS,
        'tweet.fields': 'public_metrics,created_at'
    }
    resp = requests.get(url, headers=SEARCH_HEADERS, params=params)
    resp.raise_for_status()
    data = resp.json().get('data', [])
    sorted_list = sorted(
        data,
        key=lambda x: x['public_metrics']['like_count'] + x['public_metrics']['retweet_count'],
        reverse=True
    )
    top = sorted_list[:1]
    return [{
        'title': t['text'][:50] + '...',
        'url': f"https://twitter.com/i/web/status/{t['id']}"
    } for t in top]


def fetch_daily_news() -> Dict[str, List[Dict]]:
    """同時回傳區塊鏈與經濟主題的每日熱門文章"""
    blockchain = fetch_top_blockchain_news()
    economy = fetch_top_economy_news()
    return {
        'blockchain': blockchain,
        'economy': economy
    }
