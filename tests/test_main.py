from typer.testing import CliRunner
from main import app

runner = CliRunner()

def test_run_portfolio_bounds():
    # Stable < 1 should fail
    result = runner.invoke(app, ["run", "--stable", "0", "--volatile", "3"])
    assert result.exit_code != 0

    # Volatile < 1 should fail
    result = runner.invoke(app, ["run", "--stable", "2", "--volatile", "-1"])
    assert result.exit_code != 0
