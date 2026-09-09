import asyncio
from unittest.mock import AsyncMock, patch

from portfolio_service import generate_portfolio

EXPLANATION_KEYS = {
    "summary",
    "base",
    "history_adjustment",
    "news_adjustment",
    "news_headline",
    "news_sentiment",
    "rsi",
    "rsi_adjustment",
    "macd",
    "signal",
    "macd_adjustment",
    "score",
    "bucket_size",
    "bucket_rank",
    "bucket_avg_score",
}


def test_generate_portfolio_attaches_explanation():
    market_data = {
        "BTCUSDT": {"variance": 0.01, "rsi": 25.0, "macd": 0.1, "signal": 0.0},
        "ETHUSDT": {"variance": 0.02, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "SOLUSDT": {"variance": 0.10, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "XRPUSDT": {"variance": 0.12, "rsi": 40.0, "macd": 0.0, "signal": 0.05},
    }
    prices = {symbol: 1.0 for symbol in market_data}
    symbols = list(market_data.keys())

    with patch("portfolio_service.load_history", return_value=[]), \
         patch("portfolio_service.get_unevaluated_records", return_value=[]), \
         patch("portfolio_service.get_tradeable_symbols", return_value=symbols), \
         patch("portfolio_service.get_latest_news", AsyncMock(return_value=[])), \
         patch("portfolio_service.fetch_all_market_data", AsyncMock(return_value=market_data)), \
         patch("portfolio_service.analyze_news_impact", return_value=[]), \
         patch("portfolio_service.get_current_prices", return_value=prices), \
         patch("portfolio_service.add_portfolio_record"):
        result = asyncio.run(
            generate_portfolio(stable_count=1, volatile_count=1, variance_percentile=50.0)
        )

    assert "error" not in result
    assert len(result["portfolio"]) == 2
    for item in result["portfolio"]:
        assert "explanation" in item
        explanation = item["explanation"]
        assert EXPLANATION_KEYS <= set(explanation.keys())
        assert explanation["summary"]
        assert item["score"] == explanation["score"]
        assert item["type"] in ("Stable", "Volatile")
        assert explanation["bucket_size"] >= 1
        assert explanation["bucket_rank"] >= 1
