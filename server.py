import asyncio
import hmac

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from slowapi.util import get_remote_address

from config import get_daily_coin_api_key
from constants import PORTFOLIO_COUNT_MAX, PORTFOLIO_GENERATE_RATE_LIMIT
from history import load_history
from portfolio_service import generate_portfolio as run_portfolio_generation
from schemas import GenerateResponse, HistoryRecord
from settings import SettingsModel, SettingsUpdate, load_settings
from settings import update_settings as apply_settings_update

app = FastAPI(title="Daily Coin API", description="API server for the Daily Coin portfolio selection and tracking system")
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIASGIMiddleware)

# Enable CORS for frontend development. Auth is the X-API-Key header, not cookies,
# so credentials are not allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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

@app.get("/api/settings", response_model=SettingsModel, dependencies=[Depends(require_api_key)])
async def get_settings():
    """
    Returns current persistent settings.
    """
    return await asyncio.to_thread(load_settings)

@app.post("/api/settings", response_model=SettingsModel, dependencies=[Depends(require_api_key)])
async def update_settings(update: SettingsUpdate):
    """
    Updates and persists settings. Only the fields that are sent change; the rest
    keep their stored value. Returns the full settings after the update.
    """
    return await asyncio.to_thread(apply_settings_update, update)

@app.get("/api/history", response_model=list[HistoryRecord], dependencies=[Depends(require_api_key)])
async def get_portfolio_history():
    """
    Returns the complete list of past portfolios and their evaluation results.
    """
    return await asyncio.to_thread(load_history)

@app.post(
    "/api/portfolio/generate",
    response_model=GenerateResponse,
    responses={502: {"description": "Binance data was unavailable; `detail` says what failed"}},
    dependencies=[Depends(require_api_key)],
)
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

    POST because it has side effects: it evaluates pending records and appends a new
    one to history. The latest saved portfolio can be read from GET /api/history.
    """
    # 0. Resolve parameters with persistent settings fallback
    persistent_settings = await asyncio.to_thread(load_settings)
    stable_val = stable if stable is not None else persistent_settings.stable_count
    volatile_val = volatile if volatile is not None else persistent_settings.volatile_count

    # Delegate to the shared portfolio service
    result = await run_portfolio_generation(
        stable_count=stable_val, 
        volatile_count=volatile_val,
        variance_percentile=persistent_settings.variance_percentile
    )

    if "error" in result:
        # The pipeline could not get usable market data from Binance
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result["error"])

    # Return only the API-relevant fields (strip internal data like 'scores', 'prices')
    return {
        "evaluation_results": result.get("evaluation_results", []),
        "held_evaluations": result.get("held_evaluations", 0),
        "news": result.get("news", []),
        "sentiment_impacts": result.get("sentiment_impacts", []),
        "portfolio": result.get("portfolio", []),
        "mock": result.get("mock", False),
    }
