import asyncio
import hmac
import json
import os
from filelock import FileLock
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from slowapi.util import get_remote_address

from config import get_daily_coin_api_key
from constants import PORTFOLIO_COUNT_MAX, PORTFOLIO_GENERATE_RATE_LIMIT
from history import load_history
from portfolio_service import generate_portfolio as run_portfolio_generation

app = FastAPI(title="Daily Coin API", description="API server for the Daily Coin portfolio selection and tracking system")
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIASGIMiddleware)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-API-Key"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    expected = get_daily_coin_api_key()
    if not expected or not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

SETTINGS_FILE = "settings.json"

class SettingsModel(BaseModel):
    stable_count: int = Field(gt=0, le=PORTFOLIO_COUNT_MAX)
    volatile_count: int = Field(gt=0, le=PORTFOLIO_COUNT_MAX)
    variance_percentile: float = 33.3

def load_settings_sync() -> SettingsModel:
    lock_path = f"{SETTINGS_FILE}.lock"
    with FileLock(lock_path):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    return SettingsModel(
                        stable_count=data.get("stable_count", 3),
                        volatile_count=data.get("volatile_count", 6),
                        variance_percentile=data.get("variance_percentile", 33.3)
                    )
            except Exception:
                pass
    return SettingsModel(stable_count=3, volatile_count=6, variance_percentile=33.3)

def save_settings_sync(settings: SettingsModel):
    lock_path = f"{SETTINGS_FILE}.lock"
    temp_path = f"{SETTINGS_FILE}.tmp"
    with FileLock(lock_path):
        with open(temp_path, "w") as f:
            json.dump(settings.model_dump(), f, indent=2)
        os.replace(temp_path, SETTINGS_FILE)

@app.get("/api/settings", response_model=SettingsModel, dependencies=[Depends(require_api_key)])
async def get_settings():
    """
    Returns current persistent settings.
    """
    return await asyncio.to_thread(load_settings_sync)

@app.post("/api/settings", response_model=SettingsModel, dependencies=[Depends(require_api_key)])
async def update_settings(settings: SettingsModel):
    """
    Updates and persists target stable and volatile coin counts.
    """
    await asyncio.to_thread(save_settings_sync, settings)
    return settings

@app.get("/api/history", dependencies=[Depends(require_api_key)])
async def get_portfolio_history():
    """
    Returns the complete list of past portfolios and their evaluation results.
    """
    return await asyncio.to_thread(load_history)

@app.get("/api/portfolio/generate", dependencies=[Depends(require_api_key)])
@limiter.limit(PORTFOLIO_GENERATE_RATE_LIMIT)
async def generate_portfolio(
    request: Request,
    stable: int | None = Query(
        default=None, gt=0, le=PORTFOLIO_COUNT_MAX, description="Number of stable coins to pick"
    ),
    volatile: int | None = Query(
        default=None, gt=0, le=PORTFOLIO_COUNT_MAX, description="Number of volatile coins to pick"
    ),
):
    """
    Evaluates past portfolios, fetches latest news/sentiment, calculates heuristic scores,
    and returns a newly recommended portfolio.
    """
    # 0. Resolve parameters with persistent settings fallback
    persistent_settings = await asyncio.to_thread(load_settings_sync)
    stable_val = stable if stable is not None else persistent_settings.stable_count
    volatile_val = volatile if volatile is not None else persistent_settings.volatile_count

    # Delegate to the shared portfolio service
    result = await run_portfolio_generation(
        stable_count=stable_val, 
        volatile_count=volatile_val,
        variance_percentile=persistent_settings.variance_percentile
    )

    if "error" in result:
        return result

    # Return only the API-relevant fields (strip internal data like 'scores', 'prices')
    return {
        "evaluation_results": result.get("evaluation_results", []),
        "news": result.get("news", []),
        "sentiment_impacts": result.get("sentiment_impacts", []),
        "portfolio": result.get("portfolio", []),
    }
