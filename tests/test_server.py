import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from server import app, SettingsModel


client = TestClient(app)


# --- Settings Endpoints ---

def test_get_settings_defaults(tmp_path, monkeypatch):
    """When no settings file exists, defaults should be returned."""
    monkeypatch.setattr("server.SETTINGS_FILE", str(tmp_path / "settings.json"))
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["stable_count"] == 3
    assert data["volatile_count"] == 6


def test_update_settings(tmp_path, monkeypatch):
    settings_file = str(tmp_path / "settings.json")
    monkeypatch.setattr("server.SETTINGS_FILE", settings_file)

    response = client.post(
        "/api/settings",
        json={"stable_count": 5, "volatile_count": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["stable_count"] == 5
    assert data["volatile_count"] == 10

    # Verify persistence
    response = client.get("/api/settings")
    assert response.json()["stable_count"] == 5


def test_get_settings_with_existing_file(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"stable_count": 2, "volatile_count": 4}))
    monkeypatch.setattr("server.SETTINGS_FILE", str(settings_file))

    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["stable_count"] == 2
    assert data["volatile_count"] == 4


# --- History Endpoint ---

def test_get_history_empty():
    with patch("server.load_history", return_value=[]):
        response = client.get("/api/history")
        assert response.status_code == 200
        assert response.json() == []


def test_get_history_with_records():
    mock_history = [
        {
            "timestamp": 12345,
            "portfolio": ["BTCUSDT"],
            "entry_prices": {"BTCUSDT": 90000.0},
            "evaluated": True,
            "performance": {"BTCUSDT": 0.05}
        }
    ]
    with patch("server.load_history", return_value=mock_history):
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["portfolio"] == ["BTCUSDT"]


# --- Portfolio Generation Endpoint ---

def test_generate_portfolio_success():
    mock_result = {
        "evaluation_results": [],
        "news": [{"title": "BTC news", "source": "CoinDesk", "link": "http://test.com", "timestamp": 123}],
        "sentiment_impacts": [],
        "portfolio": [
            {"coin": "BTCUSDT", "display_name": "BTC", "type": "Stable", "price": 90000.0, "score": 15.0, "rsi": 50.0, "variance": 0.02}
        ],
        "scores": {"BTCUSDT": 15.0},
        "prices": {"BTCUSDT": 90000.0},
        "final_stable": ["BTCUSDT"],
        "final_volatile": [],
        "market_data": {},
    }

    with patch("server.run_portfolio_generation", AsyncMock(return_value=mock_result)), \
         patch("server.load_settings_sync", return_value=SettingsModel(stable_count=3, volatile_count=6)):
        response = client.get("/api/portfolio/generate")
        assert response.status_code == 200
        data = response.json()
        assert "portfolio" in data
        assert len(data["portfolio"]) == 1
        assert data["portfolio"][0]["coin"] == "BTCUSDT"
        # Internal fields should be stripped
        assert "scores" not in data
        assert "prices" not in data


def test_generate_portfolio_with_params():
    mock_result = {
        "evaluation_results": [],
        "news": [],
        "sentiment_impacts": [],
        "portfolio": [
            {"coin": "ETHUSDT", "display_name": "ETH", "type": "Volatile", "price": 3000.0, "score": 10.0, "rsi": 50.0, "variance": 0.05}
        ],
        "scores": {},
        "prices": {},
        "final_stable": [],
        "final_volatile": ["ETHUSDT"],
        "market_data": {},
    }

    with patch("server.run_portfolio_generation", AsyncMock(return_value=mock_result)) as mock_gen, \
         patch("server.load_settings_sync", return_value=SettingsModel(stable_count=3, volatile_count=6)):
        response = client.get("/api/portfolio/generate?stable=2&volatile=4")
        assert response.status_code == 200
        # Verify the service was called with the query params
        mock_gen.assert_called_once_with(stable_count=2, volatile_count=4, variance_percentile=33.3)


def test_generate_portfolio_error():
    mock_result = {"error": "Could not fetch valid symbols from Binance."}

    with patch("server.run_portfolio_generation", AsyncMock(return_value=mock_result)), \
         patch("server.load_settings_sync", return_value=SettingsModel(stable_count=3, volatile_count=6)):
        response = client.get("/api/portfolio/generate")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Could not fetch valid symbols" in data["error"]


def test_generate_portfolio_uses_settings_fallback():
    """When no query params are given, should use persistent settings."""
    mock_result = {
        "evaluation_results": [],
        "news": [],
        "sentiment_impacts": [],
        "portfolio": [
            {"coin": "BTCUSDT", "display_name": "BTC", "type": "Stable", "price": 90000.0, "score": 15.0, "rsi": 50.0, "variance": 0.02}
        ],
        "scores": {"BTCUSDT": 15.0},
        "prices": {"BTCUSDT": 90000.0},
        "final_stable": ["BTCUSDT"],
        "final_volatile": [],
        "market_data": {},
    }

    with patch("server.run_portfolio_generation", AsyncMock(return_value=mock_result)) as mock_gen, \
         patch("server.load_settings_sync", return_value=SettingsModel(stable_count=5, volatile_count=8)):
        response = client.get("/api/portfolio/generate")
        assert response.status_code == 200
        # Should use the settings values
        mock_gen.assert_called_once_with(stable_count=5, volatile_count=8, variance_percentile=33.3)
