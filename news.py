import asyncio
import calendar
import logging
import re

import feedparser

from constants import (
    NEWS_AMBIGUOUS_TICKERS,
    NEWS_ANALYZE_LIMIT,
    NEWS_TICKER_MIN_LENGTH,
    VADER_CRYPTO_LEXICON,
    VADER_MULTIPLIER,
    VADER_THRESHOLD,
)

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

# Coin names, matched case-insensitively on word boundaries. Only names that point
# at one coin belong here: an exchange or company name ("binance") moves headlines
# that are not about the coin.
_NAME_ALIASES = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "binance coin": "BNBUSDT",
    "bnb chain": "BNBUSDT",
    "cardano": "ADAUSDT",
    "ripple": "XRPUSDT",
    "solana": "SOLUSDT",
    "chainlink": "LINKUSDT",
    "avalanche": "AVAXUSDT",
    "uniswap": "UNIUSDT",
    "polkadot": "DOTUSDT",
    "litecoin": "LTCUSDT",
    "polygon": "POLUSDT",
    "cosmos": "ATOMUSDT",
    "dogecoin": "DOGEUSDT",
    "dog wif hat": "WIFUSDT",
    "dogwifhat": "WIFUSDT",
    "shiba inu": "SHIBUSDT",
    "shiba": "SHIBUSDT",
    "pepe": "PEPEUSDT",
    "floki": "FLOKIUSDT",
    "bonk": "BONKUSDT",
    "aave": "AAVEUSDT",
    "toncoin": "TONUSDT",
    "tron": "TRXUSDT",
    "arbitrum": "ARBUSDT",
    "aptos": "APTUSDT",
    "hyperliquid": "HYPEUSDT",
    "filecoin": "FILUSDT",
    "worldcoin": "WLDUSDT",
    "celestia": "TIAUSDT",
    "injective": "INJUSDT",
    "pancakeswap": "CAKEUSDT",
    "apecoin": "APEUSDT",
    "hedera": "HBARUSDT",
    "algorand": "ALGOUSDT",
    "kaspa": "KASUSDT",
    "near protocol": "NEARUSDT",
    "internet computer": "ICPUSDT",
}

_ALIAS_PATTERNS = [
    (re.compile(r"\b" + re.escape(name) + r"\b"), symbol)
    for name, symbol in _NAME_ALIASES.items()
]

_TOKEN_RE = re.compile(r"\$?[A-Za-z0-9]+")


def build_ticker_map(tradeable_symbols):
    """Maps upper-case base tickers ("BTC") to their tradeable symbol ("BTCUSDT")."""
    return {symbol[:-4].upper(): symbol for symbol in tradeable_symbols or []}


def find_mentioned_symbols(headline, ticker_map=None):
    """
    Symbols a headline is about.

    Names from _NAME_ALIASES match in any case. Tickers are stricter, because many
    are ordinary words or single letters (NOT, MOVE, HOME, S):
    - "$TICKER" always counts, in any case.
    - A bare ticker counts only if it is written in upper case in a headline that
      is not all upper case, is at least NEWS_TICKER_MIN_LENGTH characters long,
      and is not listed in NEWS_AMBIGUOUS_TICKERS.
    """
    found = set()
    headline_lower = headline.lower()
    for pattern, symbol in _ALIAS_PATTERNS:
        if pattern.search(headline_lower):
            found.add(symbol)

    if ticker_map:
        # In an all-caps headline, upper case says nothing about which words are tickers
        mixed_case = any(char.islower() for char in headline)
        for token in _TOKEN_RE.findall(headline):
            symbol = None
            if token.startswith("$"):
                symbol = ticker_map.get(token[1:].upper())
            elif (
                mixed_case
                and len(token) >= NEWS_TICKER_MIN_LENGTH
                and token == token.upper()
                and token not in NEWS_AMBIGUOUS_TICKERS
            ):
                symbol = ticker_map.get(token)
            if symbol:
                found.add(symbol)

    return found


async def get_latest_news(limit=NEWS_ANALYZE_LIMIT):
    """
    Newest headlines across RSS_FEEDS, newest first: at most ``limit`` per feed and
    ``limit`` in total. Timestamps are Unix seconds (UTC); undated entries get 0
    and sort last. A feed that fails is logged and skipped.
    """
    # Run the blocking feedparser.parse calls concurrently in background threads
    tasks = [asyncio.to_thread(feedparser.parse, url) for url in RSS_FEEDS]
    feeds = await asyncio.gather(*tasks, return_exceptions=True)

    articles = []
    for url, feed in zip(RSS_FEEDS, feeds, strict=True):
        if isinstance(feed, Exception) or feed is None:
            logging.warning(f"News feed {url} could not be fetched: {feed!r}")
            continue
        try:
            if getattr(feed, 'bozo', 0) == 1 and not feed.entries:
                logging.warning(
                    f"News feed {url} returned no entries: {getattr(feed, 'bozo_exception', 'malformed feed')!r}"
                )
                continue
            for entry in feed.entries[:limit]:
                # feedparser's *_parsed values are UTC struct_time; timegm keeps them UTC
                # (time.mktime would read them as local time)
                dt_struct = entry.get('published_parsed') or entry.get('updated_parsed')
                timestamp = calendar.timegm(dt_struct) if dt_struct else 0
                    
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
        except Exception as exc:
            logging.warning(f"News feed {url} could not be parsed: {exc!r}")

    articles.sort(key=lambda x: x['timestamp'], reverse=True)
    return articles[:limit]

def analyze_news_impact(articles, tradeable_symbols=None):
    impacts = []
    analyzer = _get_analyzer()
    if not analyzer:
        return impacts
        
    ticker_map = build_ticker_map(tradeable_symbols)
    coin_compounds = {}

    for article in articles:
        headline = article.get("title", "")
        found_symbols = find_mentioned_symbols(headline, ticker_map)

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
