import feedparser
import time
import re
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    GLOBAL_ANALYZER = SentimentIntensityAnalyzer()
except ImportError:
    GLOBAL_ANALYZER = None

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

KEYWORD_MAP = {
    "bitcoin": "BTCUSDT", "btc": "BTCUSDT",
    "ethereum": "ETHUSDT", "eth": "ETHUSDT",
    "binance": "BNBUSDT", "bnb": "BNBUSDT",
    "cardano": "ADAUSDT", "ada": "ADAUSDT",
    "ripple": "XRPUSDT", "xrp": "XRPUSDT",
    "solana": "SOLUSDT", "sol": "SOLUSDT",
    "chainlink": "LINKUSDT", "link": "LINKUSDT",
    "avalanche": "AVAXUSDT", "avax": "AVAXUSDT",
    "uniswap": "UNIUSDT", "uni": "UNIUSDT",
    "polkadot": "DOTUSDT", "dot": "DOTUSDT",
    "litecoin": "LTCUSDT", "ltc": "LTCUSDT",
    "polygon": "MATICUSDT", "matic": "MATICUSDT",
    "cosmos": "ATOMUSDT", "atom": "ATOMUSDT",
    "sui": "SUIUSDT",
    "hype": "HYPEUSDT",
    "pepe": "PEPEUSDT",
    "shiba": "SHIBUSDT", "shib": "SHIBUSDT",
    "dogecoin": "DOGEUSDT", "doge": "DOGEUSDT",
    "dogwifhat": "WIFUSDT", "wif": "WIFUSDT",
    "bonk": "BONKUSDT",
    "floki": "FLOKIUSDT"
}

def get_latest_news(limit=5):
    articles = []
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            if getattr(feed, 'bozo', 0) == 1 and not feed.entries:
                continue
            for entry in feed.entries[:limit]:
                dt_struct = entry.get('published_parsed') or entry.get('updated_parsed')
                if dt_struct:
                    timestamp = time.mktime(dt_struct)
                else:
                    timestamp = 0
                    
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
            
    articles.sort(key=lambda x: x['timestamp'], reverse=True)
    return articles[:limit]

def analyze_news_impact(articles):
    impacts = []
    if not GLOBAL_ANALYZER:
        return impacts
        
    for article in articles:
        headline = article.get("title", "")
        words = re.findall(r'\b\w+\b', headline.lower())
        
        found_symbols = set()
        for word in words:
            if word in KEYWORD_MAP:
                found_symbols.add(KEYWORD_MAP[word])
                
        if found_symbols:
            sentiment = GLOBAL_ANALYZER.polarity_scores(headline)
            compound = sentiment['compound']
            
            if abs(compound) > 0.1:
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
