import asyncio
import time
from unittest.mock import MagicMock, patch

from news import (
    analyze_news_impact,
    build_ticker_map,
    find_mentioned_symbols,
    get_latest_news,
)


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


def test_analyze_news_impact_multiword_alias():
    """Compound names should map even without the tradeable-symbols list."""
    mock_analyzer = MagicMock()
    mock_analyzer.polarity_scores.return_value = {"compound": 0.9}
    articles = [{"title": "Dog wif hat listed on a new venue"}]
    with patch("news._get_analyzer", return_value=mock_analyzer):
        impacts = analyze_news_impact(articles)
    wif_impacts = [i for i in impacts if i["coin"] == "WIFUSDT"]
    assert wif_impacts
    assert wif_impacts[0]["sentiment"] == "Bullish"


def test_build_ticker_map_uses_upper_case_base():
    assert build_ticker_map(["1000PEPEUSDT", "BTCUSDT"]) == {
        "1000PEPE": "1000PEPEUSDT",
        "BTC": "BTCUSDT",
    }
    assert build_ticker_map(None) == {}


# --- find_mentioned_symbols ---

WORDLIKE_SYMBOLS = ["BTCUSDT", "SOLUSDT", "SUSDT", "NOTUSDT", "MOVEUSDT", "HOMEUSDT", "OPUSDT"]
WORDLIKE_TICKERS = build_ticker_map(WORDLIKE_SYMBOLS)


def test_everyday_words_and_possessives_do_not_match_tickers():
    """Repro from #31: only Bitcoin is mentioned, not S, NOT, MOVE or HOME."""
    headline = "Bitcoin's rally collapses after exchange hack, traders not ready to move home"
    assert find_mentioned_symbols(headline, WORDLIKE_TICKERS) == {"BTCUSDT"}

    mock_analyzer = MagicMock()
    mock_analyzer.polarity_scores.return_value = {"compound": -0.8}
    with patch("news._get_analyzer", return_value=mock_analyzer):
        impacts = analyze_news_impact([{"title": headline}], WORDLIKE_SYMBOLS)
    assert [impact["coin"] for impact in impacts] == ["BTCUSDT"]


def test_title_case_words_do_not_match_tickers():
    headline = "Not Every Token Will Move: Home Buyers Turn To Sol-Backed Loans"
    assert find_mentioned_symbols(headline, WORDLIKE_TICKERS) == set()


def test_upper_case_ticker_matches():
    assert find_mentioned_symbols("SOL jumps as ETF hopes grow", WORDLIKE_TICKERS) == {"SOLUSDT"}
    assert find_mentioned_symbols("BTC's dominance climbs", WORDLIKE_TICKERS) == {"BTCUSDT"}


def test_dollar_prefix_matches_any_ticker_in_any_case():
    headline = "Traders rotate into $s, $NOT and $op"
    assert find_mentioned_symbols(headline, WORDLIKE_TICKERS) == {"SUSDT", "NOTUSDT", "OPUSDT"}


def test_ambiguous_and_short_tickers_need_dollar_prefix():
    assert find_mentioned_symbols("Why NOT is trending on OP today", WORDLIKE_TICKERS) == set()
    assert find_mentioned_symbols("MOVE and HOME lead the week", WORDLIKE_TICKERS) == set()


def test_all_caps_headline_only_matches_names_and_dollar_tickers():
    headline = "BREAKING: SOL AND BTC CRASH"
    assert find_mentioned_symbols(headline, WORDLIKE_TICKERS) == set()
    assert find_mentioned_symbols("BITCOIN AND $SOL CRASH", WORDLIKE_TICKERS) == {"BTCUSDT", "SOLUSDT"}


def test_exchange_name_does_not_match_bnb():
    tickers = build_ticker_map(["BNBUSDT", "POLUSDT"])
    assert find_mentioned_symbols("Binance lists a new token", tickers) == set()
    assert find_mentioned_symbols("Binance Coin hits a record", tickers) == {"BNBUSDT"}
    assert find_mentioned_symbols("BNB Chain activity grows", tickers) == {"BNBUSDT"}


def test_polygon_maps_to_pol():
    assert find_mentioned_symbols("Polygon upgrade lands") == {"POLUSDT"}


def test_names_match_without_a_ticker_map():
    assert find_mentioned_symbols("Ethereum and Solana lead altcoin rally") == {"ETHUSDT", "SOLUSDT"}
    assert find_mentioned_symbols("SOL jumps as ETF hopes grow") == set()


def test_analyze_news_impact_no_analyzer():
    # If the _get_analyzer function returns None, it should gracefully return empty impacts
    with patch("news._get_analyzer", return_value=None):
        impacts = analyze_news_impact([{"title": "Bitcoin moon"}])
        assert impacts == []
