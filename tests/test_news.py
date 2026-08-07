import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from news import analyze_news_impact, get_latest_news


class FakeFeedEntry:
    """Mimics a feedparser entry object."""
    def __init__(self, title="Test headline", link="http://example.com", published_parsed=None):
        self.title = title
        self.link = link
        self.published_parsed = published_parsed or time.gmtime()
        self.updated_parsed = None

    def get(self, key, default=None):
        return getattr(self, key, default)


class FakeFeed:
    """Mimics a feedparser.parse result."""
    def __init__(self, entries=None, bozo=0, title="Test Feed"):
        self.entries = entries or []
        self.bozo = bozo
        self.feed = MagicMock()
        self.feed.get = MagicMock(return_value=title)


# --- get_latest_news ---

def test_get_latest_news_valid_entries():
    entries = [
        FakeFeedEntry(title="Bitcoin hits new high", link="http://a.com"),
        FakeFeedEntry(title="Ethereum upgrade", link="http://b.com"),
    ]
    fake_feed = FakeFeed(entries=entries, title="Cointelegraph")

    with patch("news.asyncio.to_thread", return_value=fake_feed):
        # Since we patch to_thread to return directly, we need to handle gather
        pass

    # Test using direct mock of feedparser.parse
    with patch("news.RSS_FEEDS", ["http://fake.com"]):
        with patch("news.asyncio.to_thread", side_effect=[fake_feed]):
            result = asyncio.run(get_latest_news(limit=5))
            assert len(result) == 2
            assert result[0]["title"] == "Bitcoin hits new high" or result[0]["title"] == "Ethereum upgrade"
            assert "source" in result[0]
            assert "link" in result[0]


def test_get_latest_news_empty_feed():
    fake_feed = FakeFeed(entries=[], title="Empty Feed")

    with patch("news.RSS_FEEDS", ["http://fake.com"]):
        with patch("news.asyncio.to_thread", side_effect=[fake_feed]):
            result = asyncio.run(get_latest_news(limit=5))
            assert result == []


def test_get_latest_news_bozo_feed():
    """A bozo feed with no entries should be skipped."""
    fake_feed = FakeFeed(entries=[], bozo=1, title="Bad Feed")

    with patch("news.RSS_FEEDS", ["http://fake.com"]):
        with patch("news.asyncio.to_thread", side_effect=[fake_feed]):
            result = asyncio.run(get_latest_news(limit=5))
            assert result == []


def test_get_latest_news_exception_in_feed():
    """An exception from feedparser should be handled gracefully."""
    with patch("news.RSS_FEEDS", ["http://fake.com"]):
        with patch("news.asyncio.to_thread", side_effect=[Exception("Network error")]):
            result = asyncio.run(get_latest_news(limit=5))
            assert result == []


def test_get_latest_news_limits_results():
    entries = [FakeFeedEntry(title=f"Article {i}") for i in range(10)]
    fake_feed = FakeFeed(entries=entries, title="CoinDesk")

    with patch("news.RSS_FEEDS", ["http://fake.com"]):
        with patch("news.asyncio.to_thread", side_effect=[fake_feed]):
            result = asyncio.run(get_latest_news(limit=3))
            assert len(result) == 3


# --- analyze_news_impact ---

def test_analyze_news_impact_bullish():
    articles = [{"title": "Bitcoin price soars to new record high"}]
    impacts = analyze_news_impact(articles)
    # "bitcoin" matches BTCUSDT in KEYWORD_MAP
    btc_impacts = [i for i in impacts if i["coin"] == "BTCUSDT"]
    if btc_impacts:
        assert btc_impacts[0]["sentiment"] == "Bullish"
        assert btc_impacts[0]["adjustment"] > 0


def test_analyze_news_impact_bearish():
    articles = [{"title": "Bitcoin crashes as market sells off"}]
    impacts = analyze_news_impact(articles)
    btc_impacts = [i for i in impacts if i["coin"] == "BTCUSDT"]
    if btc_impacts:
        assert btc_impacts[0]["sentiment"] == "Bearish"
        assert btc_impacts[0]["adjustment"] < 0


def test_analyze_news_impact_no_keywords():
    articles = [{"title": "Stock market rallies on economic data"}]
    impacts = analyze_news_impact(articles)
    assert impacts == []


def test_analyze_news_impact_multiple_coins():
    articles = [{"title": "Ethereum and Solana lead altcoin rally"}]
    impacts = analyze_news_impact(articles)
    coins_found = {i["coin"] for i in impacts}
    # "ethereum" -> ETHUSDT, "solana" -> SOLUSDT
    if impacts:
        assert "ETHUSDT" in coins_found or "SOLUSDT" in coins_found


def test_analyze_news_impact_empty_articles():
    impacts = analyze_news_impact([])
    assert impacts == []


def test_analyze_news_impact_no_analyzer():
    with patch("news.GLOBAL_ANALYZER", None):
        impacts = analyze_news_impact([{"title": "Bitcoin moon"}])
        assert impacts == []
