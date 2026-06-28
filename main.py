import sys
import os
import asyncio

if sys.platform == "win32":
    os.system("chcp 65001 >nul")
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import typer
from rich.console import Console
from rich.table import Table
from datetime import datetime

from logic import pick_portfolio, evaluate_performance, load_coin_scores
from history import add_portfolio_record, load_history, save_history, get_unevaluated_records
from news import get_latest_news, analyze_news_impact
from binance_client import get_tradeable_symbols, get_current_prices, fetch_all_market_data

console = Console()
app = typer.Typer()

async def async_run_portfolio(stable_count: int, volatile_count: int):
    # 1. Evaluate past portfolios
    console.print("Checking for previous portfolios to evaluate...")
    unevaluated = get_unevaluated_records()
    history = load_history()
    
    if unevaluated:
        # Gather all unique coins to fetch prices once
        all_coins = set()
        for record in unevaluated:
            all_coins.update(record["portfolio"])
        
        current_prices = get_current_prices(list(all_coins))
        updated_history, results = evaluate_performance(unevaluated, current_prices, history)
        save_history(updated_history)
        
        console.print(f"Evaluated {len(results)} past portfolio(s).")
        for res in results:
            table = Table(title="Past Portfolio Performance")
            table.add_column("Coin", style="cyan")
            table.add_column("Change", justify="right")
            
            for coin, p_change in res["performance"].items():
                color = "green" if p_change > 0 else "red"
                pct = f"{p_change * 100:.2f}%"
                table.add_row(coin.replace("USDT", ""), f"[{color}]{pct}[/{color}]")
            console.print(table)
    else:
        console.print("No unevaluated past portfolios found.")
        
    console.print("\n[bold yellow]Fetching latest crypto news and market data concurrently...[/bold yellow]")
    
    # 2. Get tradeable symbols
    valid_symbols = get_tradeable_symbols(limit=100)
    if not valid_symbols:
        console.print("[bold red]Could not fetch valid symbols from Binance.[/bold red]")
        return
        
    # Run news fetching and market data fetching concurrently
    news_task = get_latest_news(limit=5)
    market_data_task = fetch_all_market_data(valid_symbols)
    
    news_items, market_data = await asyncio.gather(news_task, market_data_task)
    
    impacts = []
    if news_items:
        news_table = Table(title="Top Crypto Headlines")
        news_table.add_column("Source", style="cyan")
        news_table.add_column("Headline", style="white")
        news_table.add_column("Link", style="blue")
        
        for item in news_items:
            news_table.add_row(item["source"], item["title"], item["link"])
        console.print(news_table)
        
        impacts = analyze_news_impact(news_items)
        if impacts:
            console.print("\n[bold yellow]Analyzing news sentiment...[/bold yellow]")
            impact_table = Table(title="News Sentiment Impact")
            impact_table.add_column("Coin", style="magenta")
            impact_table.add_column("Headline Snippet", style="white")
            impact_table.add_column("Sentiment", style="cyan")
            impact_table.add_column("Score Adj.", justify="right")
            
            for imp in impacts:
                color = "green" if imp["adjustment"] > 0 else "red"
                adj_str = f"[{color}]{imp['adjustment']:+.2f}[/{color}]"
                snippet = imp["headline"][:45] + "..." if len(imp["headline"]) > 45 else imp["headline"]
                impact_table.add_row(imp["coin"].replace("USDT", ""), snippet, imp["sentiment"], adj_str)
            console.print(impact_table)
    else:
        console.print("No news available right now.")
        
    console.print("\n[bold yellow]Generating new portfolio...[/bold yellow]")
    
    # 3. Categorize symbols based on variance
    sorted_symbols = sorted([s for s in valid_symbols if s in market_data], key=lambda x: market_data[x]["variance"])
    if not sorted_symbols:
        console.print("[bold red]No valid market data retrieved from Binance.[/bold red]")
        return
        
    third = max(1, len(sorted_symbols) // 3)
    available_stable = sorted_symbols[:third]
    available_volatile = sorted_symbols[third:]
    
    universe = available_stable + available_volatile
    
    # Reload history because it might have been updated in evaluation
    history = load_history()
    scores = load_coin_scores(universe, history, impacts, market_data)
    
    # Call the pure pick_portfolio
    stable_picks, volatile_picks = pick_portfolio(
        available_stable, available_volatile, scores, 
        stable_count=stable_count, volatile_count=volatile_count
    )
    
    # 4. Verify and resolve non-zero entry prices for chosen candidates
    portfolio = stable_picks + volatile_picks
    prices = get_current_prices(portfolio)
    
    tried_symbols = set(portfolio)
    
    final_stable = []
    for coin in stable_picks:
        price = prices.get(coin, 0.0)
        if price > 0:
            final_stable.append(coin)
        else:
            console.print(f"[bold red]Discarded stable coin {coin.replace('USDT', '')} due to invalid price ($0.0). Finding replacement...[/bold red]")
            
    remaining_stable = [s for s in available_stable if s not in tried_symbols]
    while len(final_stable) < stable_count and remaining_stable:
        remaining_stable.sort(key=lambda x: scores.get(x, 10.0), reverse=True)
        candidate = remaining_stable.pop(0)
        tried_symbols.add(candidate)
        cand_price = get_current_prices([candidate]).get(candidate, 0.0)
        if cand_price > 0:
            final_stable.append(candidate)
            prices[candidate] = cand_price
            console.print(f"[bold green]Selected replacement stable coin: {candidate.replace('USDT', '')} (${cand_price:.4f})[/bold green]")
            
    final_volatile = []
    for coin in volatile_picks:
        price = prices.get(coin, 0.0)
        if price > 0:
            final_volatile.append(coin)
        else:
            console.print(f"[bold red]Discarded volatile coin {coin.replace('USDT', '')} due to invalid price ($0.0). Finding replacement...[/bold red]")
            
    remaining_volatile = [v for v in available_volatile if v not in tried_symbols]
    while len(final_volatile) < volatile_count and remaining_volatile:
        remaining_volatile.sort(key=lambda x: scores.get(x, 10.0), reverse=True)
        candidate = remaining_volatile.pop(0)
        tried_symbols.add(candidate)
        cand_price = get_current_prices([candidate]).get(candidate, 0.0)
        if cand_price > 0:
            final_volatile.append(candidate)
            prices[candidate] = cand_price
            console.print(f"[bold green]Selected replacement volatile coin: {candidate.replace('USDT', '')} (${cand_price:.4f})[/bold green]")
            
    final_portfolio = final_stable + final_volatile
    
    if not final_portfolio:
        console.print("[bold red]Could not find any coins with non-zero prices.[/bold red]")
        return
        
    add_portfolio_record(final_portfolio, prices)
    
    # Print recommended portfolio
    p_table = Table(title="Recommended Portfolio")
    p_table.add_column("Coin", style="magenta")
    p_table.add_column("Type", style="cyan")
    p_table.add_column("Entry Price", justify="right")
    p_table.add_column("Heuristic Score", justify="right")
    
    stable_set = set(final_stable)
    for coin in final_portfolio:
        c_type = "Stable" if coin in stable_set else "Volatile"
        price_str = f"${prices.get(coin, 0):.4f}"
        score_str = f"{scores.get(coin, 10.0):.2f}"
        p_table.add_row(coin.replace("USDT", ""), c_type, price_str, score_str)
        
    console.print(p_table)
    console.print("\n[bold green]Done! Run again later to evaluate these picks and get a new portfolio.[/bold green]")

@app.command(name="run")
def run_portfolio(
    stable: int = typer.Option(3, min=1, help="Number of stable coins to pick"),
    volatile: int = typer.Option(6, min=1, help="Number of volatile coins to pick")
):
    """
    Evaluates the previous portfolio (if any) and generates a new portfolio of coins.
    """
    console.print("[bold blue]Starting Crypto Portfolio Generator...[/bold blue]")
    asyncio.run(async_run_portfolio(stable_count=stable, volatile_count=volatile))

@app.command(name="history")
def show_history():
    """
    Shows the performance of all past evaluated portfolios.
    """
    history = load_history()
    evaluated = [r for r in history if r.get("evaluated") and "performance" in r]
    
    if not evaluated:
        console.print("No evaluated past portfolios found.")
        return
        
    for record in evaluated:
        dt = datetime.fromtimestamp(record["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
        table = Table(title=f"Portfolio from {dt}")
        table.add_column("Coin", style="cyan")
        table.add_column("Change", justify="right")
        
        for coin, p_change in record["performance"].items():
            color = "green" if p_change > 0 else "red"
            pct = f"{p_change * 100:.2f}%"
            table.add_row(coin.replace("USDT", ""), f"[{color}]{pct}[/{color}]")
        console.print(table)
        console.print("")

if __name__ == "__main__":
    app()
