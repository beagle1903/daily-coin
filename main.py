import sys
import os
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
from logic import pick_portfolio, evaluate_performance
from history import add_portfolio_record, load_history
from news import get_latest_news, analyze_news_impact

console = Console()
app = typer.Typer()

@app.command(name="run")
def run_portfolio(
    stable: int = typer.Option(3, min=1, help="Number of stable coins to pick"),
    volatile: int = typer.Option(6, min=1, help="Number of volatile coins to pick")
):
    """
    Evaluates yesterday's portfolio (if any) and generates a new portfolio of coins.
    """
    console.print("[bold blue]Starting Daily Crypto Portfolio...[/bold blue]")
    
    # 1. Evaluate past portfolios
    console.print("Checking for previous portfolios to evaluate...")
    results = evaluate_performance()
    
    if results:
        console.print(f"Evaluated {len(results)} past portfolio(s).")
        for res in results:
            table = Table(title="Past Portfolio Performance")
            table.add_column("Coin", style="cyan")
            table.add_column("24h Change", justify="right")
            
            for coin, p_change in res["performance"].items():
                color = "green" if p_change > 0 else "red"
                pct = f"{p_change * 100:.2f}%"
                table.add_row(coin.replace("USDT", ""), f"[{color}]{pct}[/{color}]")
            console.print(table)
    else:
        console.print("No unevaluated past portfolios found.")
        
    console.print("\n[bold yellow]Fetching latest crypto news...[/bold yellow]")
    news_items = get_latest_news(limit=5)
    
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
        
    console.print("\n[bold yellow]Generating today's portfolio...[/bold yellow]")
    
    try:
        portfolio, prices, stable_set, scores = pick_portfolio(impacts, stable_count=stable, volatile_count=volatile)
    except Exception as e:
        console.print(f"[bold red]Error generating portfolio: {e}[/bold red]")
        return
        
    if not portfolio:
        console.print("[bold red]Could not fetch valid symbols from Binance.[/bold red]")
        return
        
    # Save today's picks
    add_portfolio_record(portfolio, prices)
    
    # Print new portfolio
    p_table = Table(title="Today's Recommended Portfolio")
    p_table.add_column("Coin", style="magenta")
    p_table.add_column("Type", style="cyan")
    p_table.add_column("Entry Price", justify="right")
    p_table.add_column("Heuristic Score", justify="right")
    
    for coin in portfolio:
        c_type = "Stable" if coin in stable_set else "Volatile"
        price_str = f"${prices.get(coin, 0):.4f}"
        score_str = f"{scores.get(coin, 10.0):.2f}"
        p_table.add_row(coin.replace("USDT", ""), c_type, price_str, score_str)
        
    console.print(p_table)
    console.print("\n[bold green]Done! Run again tomorrow to evaluate these picks and get a new portfolio.[/bold green]")

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
        table.add_column("24h Change", justify="right")
        
        for coin, p_change in record["performance"].items():
            color = "green" if p_change > 0 else "red"
            pct = f"{p_change * 100:.2f}%"
            table.add_row(coin.replace("USDT", ""), f"[{color}]{pct}[/{color}]")
        console.print(table)
        console.print("")

if __name__ == "__main__":
    app()
