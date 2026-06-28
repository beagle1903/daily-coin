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
    mock_news = [
        {"title": "Bitcoin bottom is in", "link": "http://test.com", "source": "CoinDesk", "timestamp": 12345678}
    ]
    mock_market_data = {
        "BTCUSDT": {"variance": 0.02, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "ETHUSDT": {"variance": 0.03, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "SOLUSDT": {"variance": 0.05, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "ADAUSDT": {"variance": 0.06, "rsi": 50.0, "macd": 0.0, "signal": 0.0},
        "XRPUSDT": {"variance": 0.07, "rsi": 50.0, "macd": 0.0, "signal": 0.0}
    }
    mock_prices = {
        "BTCUSDT": 90000.0, "ETHUSDT": 3000.0, "SOLUSDT": 180.0, "ADAUSDT": 0.5, "XRPUSDT": 1.0
    }
    
    with patch("main.get_tradeable_symbols", return_value=["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]), \
         patch("main.get_latest_news", AsyncMock(return_value=mock_news)), \
         patch("main.fetch_all_market_data", AsyncMock(return_value=mock_market_data)), \
         patch("main.get_current_prices", return_value=mock_prices), \
         patch("main.get_unevaluated_records", return_value=[]), \
         patch("main.load_history", return_value=[]), \
         patch("main.add_portfolio_record") as mock_add_record:
         
        result = runner.invoke(app, ["run", "--stable", "2", "--volatile", "2"])
        
        assert result.exit_code == 0
        assert "Starting Crypto Portfolio Generator" in result.output
        assert "Top Crypto Headlines" in result.output
        assert "Recommended Portfolio" in result.output
        mock_add_record.assert_called_once()
