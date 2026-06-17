import pytest
from binance_client import calculate_rsi, calculate_macd

def test_calculate_rsi_short_list():
    # Less than period + 1 (15 elements)
    closes = [100.0] * 10
    assert calculate_rsi(closes) == 50.0

def test_calculate_rsi_all_gains():
    # 20 elements, all increasing
    closes = [float(i) for i in range(20)]
    assert calculate_rsi(closes) == 100.0

def test_calculate_rsi_all_losses():
    # 20 elements, all decreasing
    closes = [float(100 - i) for i in range(20)]
    assert calculate_rsi(closes) == 0.0

def test_calculate_macd_short_list():
    # Less than 35 elements
    closes = [100.0] * 30
    macd, signal = calculate_macd(closes)
    assert macd == 0.0
    assert signal == 0.0

def test_calculate_macd_sufficient_data():
    # 50 elements, flat series should produce 0.0 MACD and signal
    closes = [100.0] * 50
    macd, signal = calculate_macd(closes)
    assert macd == 0.0
    assert signal == 0.0
