"""
新聞擷取模組
提供：
 - fetch_top_blockchain_news(): 回傳區塊鏈主題最高互動推文
 - fetch_top_economy_news(): 回傳經濟主題最高互動推文
"""
from typing import List, Dict

# TODO: 使用 Twitter API v2 或 News API


def fetch_top_blockchain_news() -> List[Dict]:
    """回傳 list[{'title': str, 'url': str}]"""
    # Placeholder 實做，之後改用正式 API
    return [{'title': '示例區塊鏈文章', 'url': 'https://twitter.com/example'}]


def fetch_top_economy_news() -> List[Dict]:
    """回傳 list[{'title': str, 'url': str}]"""
    return [{'title': '示例經濟文章', 'url': 'https://twitter.com/example2'}]
