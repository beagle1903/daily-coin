# Security Review

## Findings
1. **Secrets Management**: Good. The project uses `dotenv` to load API keys securely from environment variables, preventing hardcoded secrets in the codebase.
2. **Input Validation**: `main.py` uses Typer for type hinting inputs like `--stable` and `--volatile`, but lacks bounds checking. A user could input negative numbers, potentially breaking downstream logic in `pick_portfolio`.
3. **Exception Handling**: Global exception catches (e.g., `except Exception as e:`) could potentially leak stack traces or internal state if logged inappropriately, though it's currently printed to console safely.
4. **Dependency Vulnerabilities**: Need to ensure third-party libraries (`binance-python`, `typer`, `feedparser`, `vaderSentiment`) are pinned to known secure versions.

## Recommendations
- Implement bound checks on CLI integer inputs.
- Use specific exception handling instead of catching base `Exception`.
- Implement rate limiting logic or backoff mechanisms for Binance API calls to avoid IP bans.
