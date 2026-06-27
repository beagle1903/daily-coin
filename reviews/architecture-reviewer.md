# Architecture Review

**Date:** 2026-06-23
**Role:** Architecture Reviewer

## Overview
This document outlines the architectural findings for the `daily-coin` CLI, assessing separation of concerns, design patterns, scalability, maintainability, and alignment with the core architectural documentation (`docs/architecture.md` and `docs/decisions.md`).

## 1. Alignment with Architecture Documentation & ADRs
- **CLI Framework:** Successfully leverages `Typer` as outlined in ADR 002. `main.py` is well-structured as an entry point.
- **Explicit Memory:** Implements explicit JSON-based memory (`history.json`) accurately based on ADR 001. The heuristic loop in `history.py` functions as intended.
- **News Aggregation & Sentiment:** Follows ADR 003 and 004 by effectively using `feedparser` and `vaderSentiment` without relying on heavy external integrations or APIs.

## 2. Separation of Concerns (SoC)
- **Strengths:** 
  - `main.py` is largely decoupled from implementation details, acting merely as a router and UI orchestrator using `rich`.
  - `news.py` is entirely self-contained and manages only RSS parsing and sentiment scoring.
- **Areas for Improvement:** 
  - **Logic Coupling:** `logic.py` is intended to contain "pure functions" (per `docs/architecture.md`), but currently it directly imports and invokes functions from `binance_client.py` and `history.py`. This tightly couples the business logic to network I/O and disk I/O.
  - **Recommendation:** Implement Dependency Injection (DI). Pass the required data (prices, variances, technical indicators, history) as arguments into the scoring and selection functions in `logic.py`. This would make `logic.py` truly pure and vastly simpler to unit test.

## 3. Design Patterns & Best Practices
- **Inconsistent Client Usage:** `binance_client.py` uses a mix of global synchronous clients (`Client`) and dynamically instantiated asynchronous clients (`AsyncClient`). 
  - The synchronous `client = Client(...)` at the module level means it is instantiated upon import, which can cause issues if environment variables are missing or if the script is imported in an environment where network access is restricted (e.g., during some tests).
  - **Recommendation:** Standardize on an asynchronous approach for all data fetching, or at least encapsulate client instantiation inside getter functions or a class.
- **Heuristic Feedback Loop:** The feedback loop is implemented accurately, modifying heuristic scores based on the 7-day performance TTL.

## 4. Scalability & Performance
- **Strengths:** The use of `asyncio` and `asyncio.gather` in `fetch_all_technical_indicators` and `fetch_all_variances` ensures that pulling klines for ~100 symbols happens concurrently, keeping the CLI extremely fast.
- **Areas for Improvement:** 
  - In `binance_client.py`, `AsyncClient.create(...)` is called inside `fetch_all_variances` and `fetch_all_technical_indicators`, creating and closing the connection for each batch. While this works, a single shared async session across the entire run would be marginally more efficient.
  - The `news.py` KEYWORD_MAP is hardcoded. While performant, this manual mapping won't scale automatically if Binance lists new popular tokens.

## 5. Maintainability
- The codebase is currently small enough that maintainability is high.
- Adding typing (`typing.Dict`, `typing.List`) to function signatures in `logic.py` and `binance_client.py` would improve developer experience, aligning with the choice of Typer which encourages extensive type hinting.

## Conclusion
The architecture is solidly aligned with the documentation and the ADRs. The primary area of concern is the lack of Dependency Injection in `logic.py`, which violates the goal of it being purely functional logic. Refactoring `logic.py` to accept raw data instead of fetching it internally would elevate the architectural soundness of the system.
