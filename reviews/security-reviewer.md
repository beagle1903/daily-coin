# Security Review: daily-coin

**Date:** 2026-08-07  
**Reviewer:** Security Review Agent

---

## 1. Missing Authentication & Rate Limiting on API
**Severity:** P1  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 47-202)  
**Issue:** The FastAPI endpoints (`/api/settings`, `/api/portfolio/generate`) lack authentication and rate limiting. Anyone with network access to the server can modify settings or repeatedly trigger the portfolio generation endpoint. This can lead to a Denial of Service (DoS) via resource exhaustion or by triggering upstream Binance API rate limits and IP bans.  
**Fix Suggestion:**
> Implement API key authentication or JWT for all FastAPI endpoints. Additionally, integrate a rate limiting library (e.g., `slowapi`) to throttle requests to the `/api/portfolio/generate` endpoint.

---

## 2. Unvalidated Input in API Parameters
**Severity:** P1  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 26-28, 70-72)  
**Issue:** The `SettingsModel` and `generate_portfolio` function accept `stable` and `volatile` counts as integers but fail to enforce boundary validations (e.g., ensuring they are positive integers). Negative or excessively large numbers could crash the underlying logic or cause Out of Memory errors.  
**Fix Suggestion:**
> Add Pydantic field validators to `SettingsModel` (e.g., `stable_count: int = Field(gt=0, le=50)`) and use FastAPI's `Query(..., gt=0, le=50)` constraints for the `/api/portfolio/generate` endpoint parameters.

---

## 3. Race Conditions and Data Corruption in JSON File Writes
**Severity:** P1  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 43-45), [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py) (Lines 17-19)  
**Issue:** The application uses plain `json.dump` to write to `settings.json` and `history.json`. Concurrent API requests can trigger these writes simultaneously, leading to race conditions and file corruption. Moreover, the writes are not atomic.  
**Fix Suggestion:**
> Use a file lock mechanism (e.g., the `filelock` library) when reading/writing JSON files. Implement atomic writes by writing the JSON data to a temporary file first, then safely renaming it to the target filename.

---

## 4. Plaintext Secrets on Disk
**Severity:** P1  
**File(s):** `.env` (Lines 1-2)  
**Issue:** The `.env` file contains plaintext Binance API credentials (`BINANCE_API_KEY` and `BINANCE_API_SECRET`). The `.gitignore` file only excludes `venv/` and `__pycache__/`, but does **NOT** include `.env`. This means API keys could be committed to version control.  
**Fix Suggestion:**
> Add `.env` to `.gitignore` immediately. Ensure the stored Binance API keys are strictly configured with read-only permissions on Binance. Rotate the currently exposed keys. Consider integrating a secure secrets manager for production deployments.

---

## 5. Insecure CORS Configuration
**Severity:** P2  
**File(s):** [`server.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/server.py) (Lines 16-22)  
**Issue:** The CORS middleware allows all methods (`allow_methods=["*"]`) and all headers (`allow_headers=["*"]`) while permitting credentials. Even though origins are restricted to localhost, this overly permissive config increases the attack surface for local CSRF exploits.  
**Fix Suggestion:**
> Restrict the CORS `allow_methods` to only the required HTTP methods (e.g., `['GET', 'POST']`) and explicitly list allowed headers instead of using wildcards.

---

## 6. Mutable Global State (`USE_MOCK_DATA`)
**Severity:** P1  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Lines 12, 26, 65, 110, 203, 215, 257)  
**Issue:** Multiple modules mutate the `USE_MOCK_DATA` global variable. In the FastAPI server context, a single transient Binance API failure permanently degrades ALL future requests to mock mode until server restart. This could create race conditions in async contexts.  
**Fix Suggestion:**
> Refactor `binance_client.py` to remove global state mutation of `USE_MOCK_DATA`. Use per-request context or implement transient error retries.

---

## 7. Recursive Fallback Pattern
**Severity:** P2  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Lines 64-66, 109-111)  
**Issue:** If the API call fails, functions like `get_tradeable_symbols` set `USE_MOCK_DATA = True` and recursively call themselves. This could stack overflow if the logic is modified improperly.  
**Fix Suggestion:**
> Replace recursive fallback with explicit if/else branching to return mock data directly.

---

## 8. Information Disclosure in Error Logging
**Severity:** P2  
**File(s):** [`binance_client.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/binance_client.py) (Lines 64, 109, 202, 256)  
**Issue:** Broad `except Exception as e:` blocks catch arbitrary errors and print the raw exception to `sys.stderr`. This can inadvertently leak sensitive runtime data or internal state details.  
**Fix Suggestion:**
> Replace plain `print` statements with Python's standard `logging` module. Log generic, user-safe error messages while keeping stack traces secure and separate.

---

## 9. History File Has No Integrity Checks
**Severity:** P2  
**File(s):** [`history.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/history.py)  
**Issue:** JSON deserialization is done without schema validation. Malformed or tampered history files could crash the application or produce incorrect results.  
**Fix Suggestion:**
> Add Pydantic model validation for history records on load.

---

## 10. No HTTPS Enforcement
**Severity:** P2  
**File(s):** [`main.py`](file:///c:/Users/burha/Documents/dev-cc/daily-coin/main.py) (Line 238)  
**Issue:** Uvicorn runs with `reload=True` and plain HTTP by default. While acceptable for local development, production deployments should enforce HTTPS.  
**Fix Suggestion:**
> Document HTTPS requirements for production. Add SSL certificate configuration options to the `serve` command.
