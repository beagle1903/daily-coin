import typer
from rich.console import Console
from rich.table import Table

from logic import pick_portfolio, evaluate_performance, load_coin_scores
from history import add_portfolio_record
from news import get_latest_news

console = Console()

def main():
    """
    Evaluates yesterday's portfolio (if any) and generates a new portfolio of 5 coins.
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
                table.add_row(coin, f"[{color}]{pct}[/{color}]")
            console.print(table)
    else:
        console.print("No unevaluated past portfolios found.")
        
    console.print("\n[bold yellow]Fetching latest crypto news...[/bold yellow]")
    news_items = get_latest_news(limit=5)
    
    if news_items:
        news_table = Table(title="Top Crypto Headlines")
        news_table.add_column("Source", style="cyan")
        news_table.add_column("Headline", style="white")
        # rich supports clickable links in some terminals using syntax: [link=URL]Text[/link]
        news_table.add_column("Link", style="blue")
        
        for item in news_items:
            news_table.add_row(item["source"], item["title"], item["link"])
        console.print(news_table)
    else:
        console.print("No news available right now.")
        
    console.print("\n[bold yellow]Generating today's portfolio...[/bold yellow]")
    
    scores = load_coin_scores()
    
    try:
        portfolio, prices = pick_portfolio()
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
    
    from logic import CONSERVATIVE
    for coin in portfolio:
        c_type = "Stable" if coin in CONSERVATIVE else "Volatile"
        price_str = f"${prices.get(coin, 0):.4f}"
        score_str = f"{scores.get(coin, 10.0):.2f}"
        p_table.add_row(coin, c_type, price_str, score_str)
        
    console.print(p_table)
    console.print("\n[bold green]Done! Run again tomorrow to evaluate these picks and get a new portfolio.[/bold green]")

if __name__ == "__main__":
    typer.run(main)
