import os
import json
import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from logic import pick_portfolio, evaluate_performance, load_coin_scores
from history import add_portfolio_record, load_history, save_history, get_unevaluated_records
from news import get_latest_news, analyze_news_impact
from binance_client import get_tradeable_symbols, get_current_prices, fetch_all_market_data

app = FastAPI(title="Daily Coin API", description="API server for the Daily Coin portfolio selection and tracking system")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SETTINGS_FILE = "settings.json"

class SettingsModel(BaseModel):
    stable_count: int
    volatile_count: int

def load_settings_sync() -> SettingsModel:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return SettingsModel(
                    stable_count=data.get("stable_count", 3),
                    volatile_count=data.get("volatile_count", 6)
                )
        except Exception:
            pass
    return SettingsModel(stable_count=3, volatile_count=6)

def save_settings_sync(settings: SettingsModel):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)

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

    evaluation_results = []
    
    # 1. Evaluate past portfolios
    unevaluated = await asyncio.to_thread(get_unevaluated_records)
    history = await asyncio.to_thread(load_history)
    
    if unevaluated:
        all_coins = set()
        for record in unevaluated:
            all_coins.update(record["portfolio"])
        
        current_prices = await asyncio.to_thread(get_current_prices, list(all_coins))
        updated_history, results = evaluate_performance(unevaluated, current_prices, history)
        await asyncio.to_thread(save_history, updated_history)
        evaluation_results = results
        
    # 2. Get tradeable symbols
    valid_symbols = await asyncio.to_thread(get_tradeable_symbols, limit=100)
    if not valid_symbols:
        return {"error": "Could not fetch valid symbols from Binance."}
        
    # Run news fetching and market data fetching concurrently
    news_task = get_latest_news(limit=5)
    market_data_task = fetch_all_market_data(valid_symbols)
    
    news_items, market_data = await asyncio.gather(news_task, market_data_task)
    
    impacts = []
    if news_items:
        impacts = analyze_news_impact(news_items)
        
    # 3. Categorize symbols based on variance
    sorted_symbols = sorted([s for s in valid_symbols if s in market_data], key=lambda x: market_data[x]["variance"])
    if not sorted_symbols:
        return {"error": "No valid market data retrieved from Binance."}
        
    third = max(1, len(sorted_symbols) // 3)
    available_stable = sorted_symbols[:third]
    available_volatile = sorted_symbols[third:]
    
    universe = available_stable + available_volatile
    
    # Reload history because it might have been updated in evaluation
    history = await asyncio.to_thread(load_history)
    scores = load_coin_scores(universe, history, impacts, market_data)
    
    # Call the pure pick_portfolio
    stable_picks, volatile_picks = pick_portfolio(
        available_stable, available_volatile, scores, 
        stable_count=stable_val, volatile_count=volatile_val
    )
    
    # 4. Verify and resolve non-zero entry prices for chosen candidates
    portfolio = stable_picks + volatile_picks
    prices = await asyncio.to_thread(get_current_prices, portfolio)
    
    tried_symbols = set(portfolio)
    
    final_stable = []
    for coin in stable_picks:
        price = prices.get(coin, 0.0)
        if price > 0:
            final_stable.append(coin)
            
    remaining_stable = [s for s in available_stable if s not in tried_symbols]
    while len(final_stable) < stable_val and remaining_stable:
        remaining_stable.sort(key=lambda x: scores.get(x, 10.0), reverse=True)
        candidate = remaining_stable.pop(0)
        tried_symbols.add(candidate)
        cand_price = (await asyncio.to_thread(get_current_prices, [candidate])).get(candidate, 0.0)
        if cand_price > 0:
            final_stable.append(candidate)
            prices[candidate] = cand_price
            
    final_volatile = []
    for coin in volatile_picks:
        price = prices.get(coin, 0.0)
        if price > 0:
            final_volatile.append(coin)
            
    remaining_volatile = [v for v in available_volatile if v not in tried_symbols]
    while len(final_volatile) < volatile_val and remaining_volatile:
        remaining_volatile.sort(key=lambda x: scores.get(x, 10.0), reverse=True)
        candidate = remaining_volatile.pop(0)
        tried_symbols.add(candidate)
        cand_price = (await asyncio.to_thread(get_current_prices, [candidate])).get(candidate, 0.0)
        if cand_price > 0:
            final_volatile.append(candidate)
            prices[candidate] = cand_price
            
    final_portfolio = final_stable + final_volatile
    
    if not final_portfolio:
        return {"error": "Could not find any coins with non-zero prices."}
        
    await asyncio.to_thread(add_portfolio_record, final_portfolio, prices)
    
    # Construct return JSON
    stable_set = set(final_stable)
    recommended_list = []
    for coin in final_portfolio:
        recommended_list.append({
            "coin": coin,
            "display_name": coin.replace("USDT", ""),
            "type": "Stable" if coin in stable_set else "Volatile",
            "price": prices.get(coin, 0.0),
            "score": scores.get(coin, 10.0),
            "rsi": market_data.get(coin, {}).get("rsi", 50.0) if market_data else 50.0,
            "variance": market_data.get(coin, {}).get("variance", 0.0) if market_data else 0.0
        })
        
    return {
        "evaluation_results": evaluation_results,
        "news": news_items,
        "sentiment_impacts": impacts,
        "portfolio": recommended_list
    }
