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
            {"coin": "BTCUSDT", "display_name": "BTC", "type": "Stable", "price": 90000.0, "score": 15.0, "rsi": 50.0, "variance": 0.02},
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

def test_run_command_error():
    mock_error_result = {"error": "Could not fetch valid symbols from Binance."}

    with patch("main.generate_portfolio", AsyncMock(return_value=mock_error_result)):
        result = runner.invoke(app, ["run", "--stable", "2", "--volatile", "2"])

        assert result.exit_code == 0
        assert "Could not fetch valid symbols" in result.output
