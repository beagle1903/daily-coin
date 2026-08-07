# constants.py

# Binance API Limits
SEMAPHORE_LIMIT = 15
SYMBOLS_CACHE_TTL = 3600  # 1 hour
MARKET_DATA_CACHE_TTL = 900  # 15 minutes
MOCK_CIRCUIT_BREAKER_SECONDS = 60

# Technical Indicators
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Scoring Parameters
SCORE_FLOOR = 1.0
SCORE_CEILING = 30.0
MAX_PER_RECORD_ADJUSTMENT = 5.0
INITIAL_SCORE = 10.0

# VADER Sentiment Analysis
VADER_THRESHOLD = 0.25
VADER_MULTIPLIER = 2.0
VADER_CRYPTO_LEXICON = {
    "moon": 2.0,
    "pump": 1.5,
    "bull": 1.5,
    "bullish": 2.0,
    "dump": -2.0,
    "bear": -1.5,
    "bearish": -2.0,
    "rug": -3.0,
    "hack": -2.5,
    "scam": -3.0,
    "rekt": -2.5
}
