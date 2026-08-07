import asyncio
import json
import os
from filelock import FileLock
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from history import load_history
from portfolio_service import generate_portfolio as run_portfolio_generation

app = FastAPI(title="Daily Coin API", description="API server for the Daily Coin portfolio selection and tracking system")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

SETTINGS_FILE = "settings.json"

class SettingsModel(BaseModel):
    stable_count: int
    volatile_count: int
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

@app.get("/api/settings", response_model=SettingsModel)
async def get_settings():
    """
    Returns current persistent settings.
    """
    return await asyncio.to_thread(load_settings_sync)

@app.post("/api/settings", response_model=SettingsModel)
async def update_settings(settings: SettingsModel):
    """
    Updates and persists target stable and volatile coin counts.
    """
    await asyncio.to_thread(save_settings_sync, settings)
    return settings

@app.get("/api/history")
async def get_portfolio_history():
    """
    Returns the complete list of past portfolios and their evaluation results.
    """
    return await asyncio.to_thread(load_history)

@app.get("/api/portfolio/generate")
async def generate_portfolio(
    stable: int = Query(None, description="Number of stable coins to pick"),
    volatile: int = Query(None, description="Number of volatile coins to pick")
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
