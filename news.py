import feedparser
import time
import re
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    SentimentIntensityAnalyzer = None

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

KEYWORD_MAP = {
    "bitcoin": "BTCUSDT", "btc": "BTCUSDT",
    "ethereum": "ETHUSDT", "eth": "ETHUSDT",
    "solana": "SOLUSDT", "sol": "SOLUSDT",
    "chainlink": "LINKUSDT", "link": "LINKUSDT",
    "avalanche": "AVAXUSDT", "avax": "AVAXUSDT",
    "uniswap": "UNIUSDT", "uni": "UNIUSDT",
    "sui": "SUIUSDT",
    "hype": "HYPEUSDT",
    "pepe": "PEPEUSDT",
    "shiba": "SHIBUSDT", "shib": "SHIBUSDT",
    "dogecoin": "DOGEUSDT", "doge": "DOGEUSDT"
}

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

def analyze_news_impact(articles):
    impacts = []
    if not SentimentIntensityAnalyzer:
        return impacts
        
    analyzer = SentimentIntensityAnalyzer()
    
    for article in articles:
        headline = article.get("title", "")
        # Extract words ignoring punctuation
        words = re.findall(r'\b\w+\b', headline.lower())
        
        found_symbols = set()
        for word in words:
            if word in KEYWORD_MAP:
                found_symbols.add(KEYWORD_MAP[word])
                
        if found_symbols:
            sentiment = analyzer.polarity_scores(headline)
            compound = sentiment['compound']
            
            # Require at least some clear sentiment to act
            if abs(compound) > 0.1:
                # Multiplier determines how strong the impact is. 
                # compound is [-1, 1], so multiplier of 2.0 means up to +/- 2.0 to heuristic score.
                adjustment = compound * 2.0
                
                for symbol in found_symbols:
                    impacts.append({
                        "coin": symbol,
                        "headline": headline,
                        "polarity": compound,
                        "adjustment": adjustment,
                        "sentiment": "Bullish" if compound > 0 else "Bearish"
                    })
    return impacts
