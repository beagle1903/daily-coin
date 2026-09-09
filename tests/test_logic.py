import pytest
from logic import load_coin_scores, pick_portfolio, evaluate_performance, compute_bucket_stats, format_pick_explanation

def test_load_coin_scores():
    universe = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    history = [{
        "evaluated": True,
        "performance": {
            "BTCUSDT": 0.05,
            "ETHUSDT": -0.02
        }
    }]
    sentiment_impacts = [
        {"coin": "BTCUSDT", "adjustment": 0.5, "headline": "Bitcoin rallies", "sentiment": "Bullish"}
    ]
    technical_indicators = {
        "BTCUSDT": {"rsi": 25.0, "macd": 0.1, "signal": 0.0},
        "ETHUSDT": {"rsi": 75.0, "macd": -0.1, "signal": 0.0},
        "SOLUSDT": {"rsi": 50.0, "macd": 0.0, "signal": 0.0}
    }

    scores, breakdowns = load_coin_scores(universe, history, sentiment_impacts, technical_indicators)
    assert scores["BTCUSDT"] == 18.5
    assert scores["ETHUSDT"] == 5.0
    assert scores["SOLUSDT"] == 10.0

    btc = breakdowns["BTCUSDT"]
    assert btc["base"] == 10.0
    assert btc["history_adjustment"] == 5.0
    assert btc["news_adjustment"] == 0.5
    assert btc["news_headline"] == "Bitcoin rallies"
    assert btc["news_sentiment"] == "Bullish"
    assert btc["rsi"] == 25.0
    assert btc["rsi_adjustment"] == 2.0
    assert btc["macd"] == 0.1
    assert btc["signal"] == 0.0
    assert btc["macd_adjustment"] == 1.0
    assert btc["score"] == 18.5

    eth = breakdowns["ETHUSDT"]
    assert eth["history_adjustment"] == -2.0
    assert eth["news_adjustment"] == 0.0
    assert eth["news_headline"] is None
    assert eth["news_sentiment"] is None
    assert eth["rsi_adjustment"] == -2.0
    assert eth["macd_adjustment"] == -1.0
    assert eth["score"] == 5.0

    sol = breakdowns["SOLUSDT"]
    assert sol["history_adjustment"] == 0.0
    assert sol["news_adjustment"] == 0.0
    assert sol["rsi_adjustment"] == 0.0
    assert sol["macd_adjustment"] == 0.0
    assert sol["score"] == 10.0

def test_pick_portfolio():
    available_stable = ["USDT", "USDC"]
    available_volatile = ["BTC", "ETH", "SOL"]
    scores = {"USDT": 10.0, "USDC": 10.0, "BTC": 10.0, "ETH": 10.0, "SOL": 10.0}
    
    stable_picks, volatile_picks = pick_portfolio(available_stable, available_volatile, scores, stable_count=1, volatile_count=2)
    assert len(stable_picks) == 1
    assert len(volatile_picks) == 2
    assert stable_picks[0] in available_stable
    assert volatile_picks[0] in available_volatile
    assert volatile_picks[1] in available_volatile

def test_evaluate_performance():
    unevaluated = [
        {
            "timestamp": 123456,
            "portfolio": ["BTCUSDT", "ETHUSDT", "DELISTEDUSDT"],
            "entry_prices": {"BTCUSDT": 100.0, "ETHUSDT": 50.0, "DELISTEDUSDT": 10.0}
        }
    ]
    current_prices = {
        "BTCUSDT": 110.0,
        "ETHUSDT": 45.0,
        "DELISTEDUSDT": 0.0
    }
    history = [
        {
            "timestamp": 123456,
            "portfolio": ["BTCUSDT", "ETHUSDT", "DELISTEDUSDT"],
            "entry_prices": {"BTCUSDT": 100.0, "ETHUSDT": 50.0, "DELISTEDUSDT": 10.0},
            "evaluated": False
        }
    ]
    
    updated_history, results = evaluate_performance(unevaluated, current_prices, history)
    
    assert len(results) == 1
    perf = results[0]["performance"]
    assert perf["BTCUSDT"] == pytest.approx(0.10)
    assert perf["ETHUSDT"] == pytest.approx(-0.10)
    assert perf["DELISTEDUSDT"] == pytest.approx(-1.0)
    
    assert updated_history[0]["evaluated"] is True
    assert updated_history[0]["performance"] == perf

def test_pick_portfolio_empty():
    stable_picks, volatile_picks = pick_portfolio([], [], {}, stable_count=1, volatile_count=2)
    assert len(stable_picks) == 0
    assert len(volatile_picks) == 0


def test_pick_portfolio_empty_stable_only():
    scores = {"BTC": 10.0, "ETH": 8.0}
    stable_picks, volatile_picks = pick_portfolio([], ["BTC", "ETH"], scores, stable_count=1, volatile_count=1)
    assert stable_picks == []
    assert len(volatile_picks) == 1
    assert volatile_picks[0] in {"BTC", "ETH"}

def test_load_coin_scores_empty_universe():
    scores, breakdowns = load_coin_scores([], [])
    assert scores == {}
    assert breakdowns == {}

def test_evaluate_performance_all_zero():
    unevaluated = [
        {
            "timestamp": 123456,
            "portfolio": ["BTCUSDT", "ETHUSDT"],
            "entry_prices": {"BTCUSDT": 0.0, "ETHUSDT": 0.0}
        }
    ]
    current_prices = {"BTCUSDT": 100.0, "ETHUSDT": 50.0}
    history = [
        {
            "timestamp": 123456,
            "portfolio": ["BTCUSDT", "ETHUSDT"],
            "entry_prices": {"BTCUSDT": 0.0, "ETHUSDT": 0.0},
            "evaluated": False
        }
    ]
    updated_history, results = evaluate_performance(unevaluated, current_prices, history, ["BTCUSDT", "ETHUSDT"])
    
    assert results[0]["performance"]["BTCUSDT"] == 0.0
    assert results[0]["performance"]["ETHUSDT"] == 0.0


def test_compute_bucket_stats_ranks_by_score_then_symbol():
    scores = {"AAAUSDT": 10.0, "BTCUSDT": 18.5, "ETHUSDT": 18.5, "SOLUSDT": 5.0}
    stats = compute_bucket_stats(["SOLUSDT", "BTCUSDT", "ETHUSDT", "AAAUSDT"], scores)
    assert stats["BTCUSDT"]["bucket_rank"] == 1
    assert stats["ETHUSDT"]["bucket_rank"] == 2
    assert stats["AAAUSDT"]["bucket_rank"] == 3
    assert stats["SOLUSDT"]["bucket_rank"] == 4
    assert stats["BTCUSDT"]["bucket_size"] == 4
    assert stats["ETHUSDT"]["bucket_size"] == 4
    assert stats["BTCUSDT"]["bucket_avg_score"] == pytest.approx((10.0 + 18.5 + 18.5 + 5.0) / 4)


def test_compute_bucket_stats_empty():
    assert compute_bucket_stats([], {"BTCUSDT": 10.0}) == {}


def test_compute_bucket_stats_missing_score_uses_initial():
    stats = compute_bucket_stats(["NEWUSDT"], {})
    assert stats["NEWUSDT"]["bucket_rank"] == 1
    assert stats["NEWUSDT"]["bucket_size"] == 1
    assert stats["NEWUSDT"]["bucket_avg_score"] == 10.0


def test_format_pick_explanation_btc_full_example():
    breakdown = {
        "base": 10.0,
        "history_adjustment": 5.0,
        "news_adjustment": 0.5,
        "news_headline": "Bitcoin rallies as ETF inflows hit a record",
        "news_sentiment": "Bullish",
        "rsi": 22.0,
        "rsi_adjustment": 2.0,
        "macd": 1.2,
        "signal": 0.8,
        "macd_adjustment": 1.0,
        "score": 18.5,
    }
    stats = {"bucket_size": 12, "bucket_rank": 3, "bucket_avg_score": 12.4}
    text = format_pick_explanation(breakdown, stats, "Stable", 33.3, "BTC")
    assert text == (
        "BTC is in the Stable bucket (lowest ~33% of 30-day variance among tradeable pairs this run). "
        "Score 18.50 is well above the Stable average of 12.40 (rank 3 of 12 by score). "
        "Past picks added a bonus of +5.00. "
        "Bullish news (Bitcoin rallies as ETF inflows hit a record) added +0.50. "
        "RSI 22.0 is oversold; +2.0. "
        "MACD is above its signal (+1.0). "
        "It was sampled with this weight, not chosen as a guaranteed top pick."
    )


def test_format_pick_explanation_omits_zero_history_and_news():
    breakdown = {
        "base": 10.0,
        "history_adjustment": 0.0,
        "news_adjustment": 0.0,
        "news_headline": None,
        "news_sentiment": None,
        "rsi": 50.0,
        "rsi_adjustment": 0.0,
        "macd": 0.0,
        "signal": 0.0,
        "macd_adjustment": 0.0,
        "score": 10.0,
    }
    stats = {"bucket_size": 5, "bucket_rank": 3, "bucket_avg_score": 10.2}
    text = format_pick_explanation(breakdown, stats, "Volatile", 33.3, "SOL")
    assert "Past picks" not in text
    assert "news" not in text
    assert "neutral; no RSI adjustment" in text
    assert "even with its signal (no MACD adjustment)" in text
    assert "near the Volatile average of 10.20" in text
    assert "highest ~33%" in text
    assert "It was sampled with this weight, not chosen as a guaranteed top pick." in text


def test_format_pick_explanation_penalty_overbought_below_signal():
    breakdown = {
        "base": 10.0,
        "history_adjustment": -2.0,
        "news_adjustment": -0.4,
        "news_headline": "ETH dumps after hack",
        "news_sentiment": "Bearish",
        "rsi": 75.0,
        "rsi_adjustment": -2.0,
        "macd": -0.1,
        "signal": 0.0,
        "macd_adjustment": -1.0,
        "score": 5.0,
    }
    stats = {"bucket_size": 8, "bucket_rank": 7, "bucket_avg_score": 11.0}
    text = format_pick_explanation(breakdown, stats, "Volatile", 33.3, "ETH")
    assert "Past picks added a penalty of -2.00." in text
    assert "Bearish news (ETH dumps after hack) added -0.40." in text
    assert "RSI 75.0 is overbought; -2.0." in text
    assert "MACD is below its signal (-1.0)." in text
    assert "well below the Volatile average of 11.00" in text


def test_format_pick_explanation_omits_average_when_bucket_empty():
    breakdown = {
        "base": 10.0,
        "history_adjustment": 0.0,
        "news_adjustment": 0.0,
        "news_headline": None,
        "news_sentiment": None,
        "rsi": 50.0,
        "rsi_adjustment": 0.0,
        "macd": 0.0,
        "signal": 0.0,
        "macd_adjustment": 0.0,
        "score": 10.0,
    }
    text = format_pick_explanation(breakdown, {}, "Stable", 33.3, "BTC")
    assert "average" not in text
    assert "rank" not in text


def test_format_pick_explanation_truncates_headline():
    headline = "A" * 90
    breakdown = {
        "base": 10.0,
        "history_adjustment": 0.0,
        "news_adjustment": 0.5,
        "news_headline": headline,
        "news_sentiment": "Bullish",
        "rsi": 50.0,
        "rsi_adjustment": 0.0,
        "macd": 0.0,
        "signal": 0.0,
        "macd_adjustment": 0.0,
        "score": 10.5,
    }
    stats = {"bucket_size": 2, "bucket_rank": 1, "bucket_avg_score": 10.0}
    text = format_pick_explanation(breakdown, stats, "Stable", 33.3, "BTC")
    assert ("A" * 80 + "...") in text
    assert ("A" * 81) not in text


def test_format_pick_explanation_mentions_ceiling_clamp():
    breakdown = {
        "base": 10.0,
        "history_adjustment": 5.0,
        "news_adjustment": 20.0,
        "news_headline": "Huge pump",
        "news_sentiment": "Bullish",
        "rsi": 20.0,
        "rsi_adjustment": 2.0,
        "macd": 1.0,
        "signal": 0.0,
        "macd_adjustment": 1.0,
        "score": 30.0,
    }
    stats = {"bucket_size": 3, "bucket_rank": 1, "bucket_avg_score": 12.0}
    text = format_pick_explanation(breakdown, stats, "Stable", 33.3, "BTC")
    assert "The total was clamped to the 30.0 score limit." in text


def test_format_pick_explanation_mentions_floor_clamp():
    breakdown = {
        "base": 10.0,
        "history_adjustment": -5.0,
        "news_adjustment": -5.0,
        "news_headline": "Rug",
        "news_sentiment": "Bearish",
        "rsi": 80.0,
        "rsi_adjustment": -2.0,
        "macd": -1.0,
        "signal": 0.0,
        "macd_adjustment": -1.0,
        "score": 1.0,
    }
    stats = {"bucket_size": 3, "bucket_rank": 3, "bucket_avg_score": 10.0}
    text = format_pick_explanation(breakdown, stats, "Volatile", 33.3, "ETH")
    assert "The total was clamped to the 1.0 score limit." in text

