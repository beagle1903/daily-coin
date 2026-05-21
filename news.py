import feedparser
import time

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

def get_latest_news(limit=5):
    articles = []
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                dt_struct = entry.get('published_parsed') or entry.get('updated_parsed')
                if dt_struct:
                    timestamp = time.mktime(dt_struct)
                else:
                    timestamp = 0
                    
                # Shorten source title for display
                source = feed.feed.get('title', 'Crypto News')
                if 'Cointelegraph' in source:
                    source = 'Cointelegraph'
                elif 'CoinDesk' in source:
                    source = 'CoinDesk'
                    
                articles.append({
                    "title": entry.get('title', 'No Title'),
                    "link": entry.get('link', ''),
                    "source": source,
                    "timestamp": timestamp
                })
        except Exception:
            pass
            
    # Sort articles by timestamp descending (newest first)
    articles.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return articles[:limit]
