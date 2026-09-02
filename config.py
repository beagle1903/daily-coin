import os

from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
DAILY_COIN_API_KEY = os.getenv("DAILY_COIN_API_KEY")

if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    print("Warning: BINANCE_API_KEY or BINANCE_API_SECRET not found in .env file. Some features might not work.")


def get_daily_coin_api_key() -> str:
    return os.getenv("DAILY_COIN_API_KEY") or ""
