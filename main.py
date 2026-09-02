import asyncio
import os
import sys

if sys.platform == "win32":
    os.system("chcp 65001 >nul")
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from history import load_history
from portfolio_service import generate_portfolio

console = Console()
app = typer.Typer()

async def async_run_portfolio(stable_count: int, volatile_count: int):
    console.print("Checking for previous portfolios to evaluate...")

    result = await generate_portfolio(stable_count=stable_count, volatile_count=volatile_count)

    if "error" in result:
        console.print(f"[bold red]{result['error']}[/bold red]")
        return

    # Display evaluation results
    evaluation_results = result.get("evaluation_results", [])
    if evaluation_results:
        console.print(f"Evaluated {len(evaluation_results)} past portfolio(s).")
        for res in evaluation_results:
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

    # Display news
    news_items = result.get("news", [])
    if news_items:
        news_table = Table(title="Top Crypto Headlines")
        news_table.add_column("Source", style="cyan")
        news_table.add_column("Headline", style="white")
        news_table.add_column("Link", style="blue")

        for item in news_items:
            news_table.add_row(item["source"], item["title"], item["link"])
        console.print(news_table)

        impacts = result.get("sentiment_impacts", [])
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

    # Display recommended portfolio
    portfolio_items = result["portfolio"]

    p_table = Table(title="Recommended Portfolio")
    p_table.add_column("Coin", style="magenta")
    p_table.add_column("Type", style="cyan")
    p_table.add_column("Entry Price", justify="right")
    p_table.add_column("Heuristic Score", justify="right")

    for item in portfolio_items:
        p_table.add_row(
            item["display_name"],
            item["type"],
            f"${item['price']:.4f}",
            f"{item['score']:.2f}",
        )

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
@app.command(name="serve")
def serve_api(
    host: str = typer.Option("127.0.0.1", help="Host to bind the server to"),
    port: int = typer.Option(8000, help="Port to bind the server to")
):
    """
    Starts the FastAPI backend server.
    """
    import uvicorn
    console.print(f"[bold green]Starting Daily Coin API Server on http://{host}:{port}...[/bold green]")
    uvicorn.run("server:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    app()
