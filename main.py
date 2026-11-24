import asyncio
import sys

if sys.platform == "win32":
    # Rich prints box-drawing characters; make sure stdout can encode them
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import logging
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from constants import MIN_EVALUATION_AGE_SECONDS, PORTFOLIO_COUNT_MAX
from formatting import format_price
from history import load_history
from portfolio_service import generate_portfolio
from settings import load_settings

logging.basicConfig(level=logging.WARNING)

console = Console()
app = typer.Typer()

def performance_table(title: str, performance: dict) -> Table:
    """Coin and percentage change for one evaluated portfolio, gains green, losses red."""
    table = Table(title=title)
    table.add_column("Coin", style="cyan")
    table.add_column("Change", justify="right")
    for coin, p_change in performance.items():
        color = "green" if p_change > 0 else "red"
        table.add_row(coin.replace("USDT", ""), f"[{color}]{p_change * 100:.2f}%[/{color}]")
    return table

async def async_run_portfolio(stable_count: int, volatile_count: int, variance_percentile: float):
    console.print("Checking for previous portfolios to evaluate...")

    result = await generate_portfolio(
        stable_count=stable_count,
        volatile_count=volatile_count,
        variance_percentile=variance_percentile,
    )

    if "error" in result:
        console.print(f"[bold red]{result['error']}[/bold red]")
        return

    is_mock = result.get("mock", False)
    if is_mock:
        console.print(
            "[bold red]Binance is unavailable: this run uses mock market data.[/bold red] "
            "The picks below are placeholders and were not saved to history."
        )

    # Display evaluation results
    evaluation_results = result.get("evaluation_results", [])
    if evaluation_results:
        console.print(f"Evaluated {len(evaluation_results)} past portfolio(s).")
        for res in evaluation_results:
            table = performance_table("Past Portfolio Performance", res["performance"])
            console.print(table)
    elif is_mock:
        console.print("Past portfolios are not evaluated against mock prices.")
    elif not result.get("held_evaluations"):
        console.print("No unevaluated past portfolios found.")

    held = result.get("held_evaluations", 0)
    if held and not is_mock:
        console.print(
            f"{held} recent portfolio(s) are less than {MIN_EVALUATION_AGE_SECONDS // 60} minutes old "
            "and will be evaluated on a later run."
        )

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
            format_price(item["price"]),
            f"{item['score']:.2f}",
        )

    console.print(p_table)
    console.print("\n[bold yellow]Why these picks[/bold yellow]")
    for item in portfolio_items:
        explanation = item.get("explanation") or {}
        summary = explanation.get("summary")
        if not summary:
            continue
        console.print(f"[magenta]{escape(str(item['display_name']))}[/magenta]  {escape(summary)}")
    if is_mock:
        console.print("\n[bold yellow]Done (mock data). Run again once Binance is reachable to get real picks.[/bold yellow]")
    else:
        console.print("\n[bold green]Done! Run again later to evaluate these picks and get a new portfolio.[/bold green]")

@app.command(name="run")
def run_portfolio(
    stable: Optional[int] = typer.Option(
        None, min=1, max=PORTFOLIO_COUNT_MAX,
        help="Number of stable coins to pick (default: saved settings)",
    ),
    volatile: Optional[int] = typer.Option(
        None, min=1, max=PORTFOLIO_COUNT_MAX,
        help="Number of volatile coins to pick (default: saved settings)",
    ),
    variance_percentile: Optional[float] = typer.Option(
        None,
        help="Percent of coins, lowest variance first, that form the stable bucket; "
             "above 0 and below 100 (default: saved settings)",
    ),
):
    """
    Evaluates the previous portfolio (if any) and generates a new portfolio of coins.

    Options that are left out use the saved settings in settings.json, which the
    dashboard also uses. Options given here apply to this run only; they are not saved.
    """
    if variance_percentile is not None and not 0 < variance_percentile < 100:
        raise typer.BadParameter(
            "must be above 0 and below 100", param_hint="--variance-percentile"
        )

    settings = load_settings()
    console.print("[bold blue]Starting Crypto Portfolio Generator...[/bold blue]")
    asyncio.run(async_run_portfolio(
        stable_count=stable if stable is not None else settings.stable_count,
        volatile_count=volatile if volatile is not None else settings.volatile_count,
        variance_percentile=(
            variance_percentile if variance_percentile is not None else settings.variance_percentile
        ),
    ))

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
        table = performance_table(f"Portfolio from {dt}", record["performance"])
        console.print(table)
        console.print("")
@app.command(name="serve")
def serve_api(
    host: str = typer.Option("127.0.0.1", help="Host to bind the server to"),
    port: int = typer.Option(8000, help="Port to bind the server to"),
    reload: bool = typer.Option(False, "--reload/--no-reload", help="Restart on code changes (development)"),
):
    """
    Starts the FastAPI backend server.
    """
    import uvicorn
    console.print(f"[bold green]Starting Daily Coin API Server on http://{host}:{port}...[/bold green]")
    uvicorn.run("server:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    app()
