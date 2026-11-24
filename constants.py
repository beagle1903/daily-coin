# constants.py

# Binance API Limits
SEMAPHORE_LIMIT = 15
SYMBOLS_CACHE_TTL = 3600  # 1 hour
MARKET_DATA_CACHE_TTL = 900  # 15 minutes
MOCK_CIRCUIT_BREAKER_SECONDS = 60
# Share of symbols that must lack kline data before a market-data fetch counts as
# an outage (circuit breaker + mock fallback). Below it, those symbols are skipped.
KLINE_FAILURE_BREAKER_RATIO = 0.5
# Timeout for one Binance request (the startup ping and each kline fetch)
BINANCE_REQUEST_TIMEOUT_SECONDS = 5.0

# Market data: the universe is the TRADEABLE_UNIVERSE_SIZE USDT pairs with the most
# volume. Each symbol fetches KLINE_LIMIT candles of KLINE_INTERVAL (360 x 4h ~ 60
# days, enough for MACD); variance uses the last VARIANCE_WINDOW_CANDLES (~30 days).
TRADEABLE_UNIVERSE_SIZE = 100
KLINE_INTERVAL = "4h"
KLINE_LIMIT = 360
VARIANCE_WINDOW_CANDLES = 180

# Technical Indicators
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
# RSI below RSI_OVERSOLD adds RSI_ADJUSTMENT to the score, above RSI_OVERBOUGHT
# subtracts it. RSI_NEUTRAL is used when a coin has no RSI.
RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0
RSI_NEUTRAL = 50.0
RSI_ADJUSTMENT = 2.0
# MACD above its signal line adds MACD_ADJUSTMENT, below it subtracts it.
MACD_ADJUSTMENT = 1.0

# Portfolio size bounds (API query params and settings)
PORTFOLIO_COUNT_MAX = 50
DEFAULT_STABLE_COUNT = 3
DEFAULT_VOLATILE_COUNT = 6
DEFAULT_VARIANCE_PERCENTILE = 33.3
# News: sentiment is scored over the newest NEWS_ANALYZE_LIMIT headlines (per feed
# and in total); only the newest NEWS_DISPLAY_LIMIT are returned for display.
NEWS_ANALYZE_LIMIT = 50
NEWS_DISPLAY_LIMIT = 5

# News headline matching (see news.find_mentioned_symbols)
# A bare ticker shorter than this only counts when written as "$TICKER".
NEWS_TICKER_MIN_LENGTH = 3
# Tickers that are everyday words or common acronyms. Even in upper case they are
# too likely to mean something else, so they also need the "$" prefix.
NEWS_AMBIGUOUS_TICKERS = {
    "ACT", "AMP", "APE", "ARK", "BAR", "BIO", "CAT", "COW", "GMT", "GPS", "HOT",
    "LIT", "MET", "NOT", "ONE", "RAD", "RAY", "RED", "SKY", "SUN", "WET",
    "CITY", "CORE", "HOME", "MOVE", "OPEN", "ORDER", "SUPER",
}

# Quote-stable pairs excluded from the tradeable USDT universe
STABLECOIN_EXCLUDED_BASES = {
    "USDC", "FDUSD", "TUSD", "BUSD", "USD1", "EUR", "DAI", "USDD", "PYUSD", "USDP", "AEUR",
}

# API rate limits
PORTFOLIO_GENERATE_RATE_LIMIT = "10/minute"

# A saved portfolio is only evaluated once it is at least this old. Younger records
# stay pending, so quick re-runs do not feed ~0% changes into the history adjustment.
MIN_EVALUATION_AGE_SECONDS = 3600  # 1 hour
# Saved portfolios older than this are dropped from history.json.
HISTORY_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days

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
