import asyncio
import re
import time

import feedparser

from constants import VADER_THRESHOLD, VADER_MULTIPLIER, VADER_CRYPTO_LEXICON

_ANALYZER_INSTANCE = None
_ANALYZER_INITIALIZED = False

def _get_analyzer():
    global _ANALYZER_INSTANCE, _ANALYZER_INITIALIZED
    if not _ANALYZER_INITIALIZED:
        _ANALYZER_INITIALIZED = True
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _ANALYZER_INSTANCE = SentimentIntensityAnalyzer()
            _ANALYZER_INSTANCE.lexicon.update(VADER_CRYPTO_LEXICON)
        except ImportError:
            _ANALYZER_INSTANCE = None
    return _ANALYZER_INSTANCE

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

def build_keyword_map(tradeable_symbols):
    """Dynamically builds a keyword map from tradeable symbols list."""
    keyword_map = {
        "bitcoin": "BTCUSDT",
        "ethereum": "ETHUSDT",
        "binance": "BNBUSDT",
        "cardano": "ADAUSDT",
        "ripple": "XRPUSDT",
        "solana": "SOLUSDT",
        "chainlink": "LINKUSDT",
        "avalanche": "AVAXUSDT",
        "uniswap": "UNIUSDT",
        "polkadot": "DOTUSDT",
        "litecoin": "LTCUSDT",
        "polygon": "MATICUSDT",
        "cosmos": "ATOMUSDT",
        "dogecoin": "DOGEUSDT",
        "dogwifhat": "WIFUSDT",
        "shiba": "SHIBUSDT"
    }
    
    if tradeable_symbols:
        for symbol in tradeable_symbols:
            base = symbol[:-4].lower()
            keyword_map[base] = symbol
            
    return keyword_map

async def get_latest_news(limit=5):
    # Run the blocking feedparser.parse calls concurrently in background threads
    tasks = [asyncio.to_thread(feedparser.parse, url) for url in RSS_FEEDS]
    feeds = await asyncio.gather(*tasks, return_exceptions=True)
    
    articles = []
    for feed in feeds:
        if isinstance(feed, Exception) or feed is None:
            continue
        try:
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

def analyze_news_impact(articles, tradeable_symbols=None):
    impacts = []
    analyzer = _get_analyzer()
    if not analyzer:
        return impacts
        
    keyword_map = build_keyword_map(tradeable_symbols)
    coin_compounds = {}
    
    for article in articles:
        headline = article.get("title", "")
        words = re.findall(r'\b\w+\b', headline.lower())
        
        found_symbols = set()
        for word in words:
            if word in keyword_map:
                found_symbols.add(keyword_map[word])
                
        if found_symbols:
            sentiment = analyzer.polarity_scores(headline)
            compound = sentiment['compound']
            
            for symbol in found_symbols:
                if symbol not in coin_compounds:
                    coin_compounds[symbol] = []
                coin_compounds[symbol].append({
                    "compound": compound,
                    "headline": headline
                })
                
    for symbol, records in coin_compounds.items():
        avg_compound = sum(r['compound'] for r in records) / len(records)
        
        if abs(avg_compound) > VADER_THRESHOLD:
            adjustment = avg_compound * VADER_MULTIPLIER
            # Use the headline from the most impactful record for display
            best_record = max(records, key=lambda r: abs(r['compound']))
            impacts.append({
                "coin": symbol,
                "headline": best_record['headline'],
                "polarity": avg_compound,
                "adjustment": adjustment,
                "sentiment": "Bullish" if avg_compound > 0 else "Bearish"
            })
            
    return impacts
