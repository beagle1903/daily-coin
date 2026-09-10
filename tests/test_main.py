from unittest.mock import patch, AsyncMock
from typer.testing import CliRunner
from main import app

runner = CliRunner()

def test_run_portfolio_bounds():
    # Stable < 1 should fail
    result = runner.invoke(app, ["run", "--stable", "0", "--volatile", "3"])
    assert result.exit_code != 0

    # Volatile < 1 should fail
    result = runner.invoke(app, ["run", "--stable", "2", "--volatile", "-1"])
    assert result.exit_code != 0

def test_run_command_success():
    mock_portfolio_result = {
        "evaluation_results": [],
        "news": [
            {"title": "Bitcoin bottom is in", "link": "http://test.com", "source": "CoinDesk", "timestamp": 12345678}
        ],
        "sentiment_impacts": [
            {"coin": "BTCUSDT", "headline": "Bitcoin bottom is in", "polarity": 0.5, "adjustment": 1.0, "sentiment": "Bullish"}
        ],
        "portfolio": [
            {
                "coin": "BTCUSDT",
                "display_name": "BTC",
                "type": "Stable",
                "price": 90000.0,
                "score": 15.0,
                "rsi": 50.0,
                "variance": 0.02,
                "explanation": {
                    "summary": "BTC is in the Stable bucket (lowest ~33% of 30-day variance among tradeable pairs this run). It was sampled with this weight, not chosen as a guaranteed top pick.",
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
                    "score": 15.0,
                    "bucket_size": 2,
                    "bucket_rank": 1,
                    "bucket_avg_score": 12.5,
                },
            },
            {"coin": "ETHUSDT", "display_name": "ETH", "type": "Volatile", "price": 3000.0, "score": 10.0, "rsi": 50.0, "variance": 0.05},
        ],
        "scores": {"BTCUSDT": 15.0, "ETHUSDT": 10.0},
        "prices": {"BTCUSDT": 90000.0, "ETHUSDT": 3000.0},
        "final_stable": ["BTCUSDT"],
        "final_volatile": ["ETHUSDT"],
        "market_data": {},
    }

    with patch("main.generate_portfolio", AsyncMock(return_value=mock_portfolio_result)):
        result = runner.invoke(app, ["run", "--stable", "2", "--volatile", "2"])

        assert result.exit_code == 0
        assert "Starting Crypto Portfolio Generator" in result.output
        assert "Top Crypto Headlines" in result.output
        assert "Recommended Portfolio" in result.output
        assert "Why these picks" in result.output
        assert "BTC is in the Stable bucket" in result.output
        assert "sampled with this weight" in result.output


def test_run_command_escapes_rich_markup_in_explanation():
    mock_portfolio_result = {
        "evaluation_results": [],
        "news": [],
        "sentiment_impacts": [],
        "portfolio": [
            {
                "coin": "BTCUSDT",
                "display_name": "BTC",
                "type": "Stable",
                "price": 90000.0,
                "score": 15.0,
                "rsi": 50.0,
                "variance": 0.02,
                "explanation": {
                    "summary": "[bold red]injected[/bold red]",
                },
            },
        ],
        "scores": {},
        "prices": {},
        "final_stable": ["BTCUSDT"],
        "final_volatile": [],
        "market_data": {},
    }

    with patch("main.generate_portfolio", AsyncMock(return_value=mock_portfolio_result)):
        result = runner.invoke(app, ["run", "--stable", "1", "--volatile", "1"])

        assert result.exit_code == 0
        assert "[bold red]injected[/bold red]" in result.output


def test_run_command_skips_why_line_when_explanation_missing():
    mock_portfolio_result = {
        "evaluation_results": [],
        "news": [],
        "sentiment_impacts": [],
        "portfolio": [
            {"coin": "BTCUSDT", "display_name": "BTC", "type": "Stable", "price": 90000.0, "score": 15.0, "rsi": 50.0, "variance": 0.02},
        ],
        "scores": {},
        "prices": {},
        "final_stable": ["BTCUSDT"],
        "final_volatile": [],
        "market_data": {},
    }
    with patch("main.generate_portfolio", AsyncMock(return_value=mock_portfolio_result)):
        result = runner.invoke(app, ["run", "--stable", "1", "--volatile", "1"])
        assert result.exit_code == 0
        assert "Recommended Portfolio" in result.output
        assert "BTC is in the Stable bucket" not in result.output


def test_run_command_error():
    mock_error_result = {"error": "Could not fetch valid symbols from Binance."}

    with patch("main.generate_portfolio", AsyncMock(return_value=mock_error_result)):
        result = runner.invoke(app, ["run", "--stable", "2", "--volatile", "2"])

        assert result.exit_code == 0
        assert "Could not fetch valid symbols" in result.output

def test_history_command():
    mock_history = [
        {
            "timestamp": 12345678,
            "portfolio": ["BTCUSDT", "ETHUSDT"],
            "entry_prices": {"BTCUSDT": 90000.0, "ETHUSDT": 3000.0},
            "evaluated": True,
            "performance": {"BTCUSDT": 0.05, "ETHUSDT": -0.02}
        }
    ]
    with patch("main.load_history", return_value=mock_history):
        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0
        assert "Portfolio from" in result.output
        assert "BTC" in result.output
        assert "ETH" in result.output
