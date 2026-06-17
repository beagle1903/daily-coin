# Business Logic Review: Financial Aid CLI

## Overview
I was tasked with deeply reviewing the codebase and recent changes to verify the correctness of the financial aid rules, user flows, and domain logic. This review cross-referenced the current implementation against the domain knowledge provided in the project documentation.

## Findings

### 1. Missing Domain Rules & Context Discrepancy
According to `AGENTS.md`, the primary context for the financial aid rules and user flows should be derived from `docs/context.md`. However, `docs/context.md` currently defines a **"Daily Crypto Portfolio CLI"** and contains no information regarding financial aid logic, eligibility criteria, student profiles, or scoring metrics. Without these explicit rules, no business logic validation can be accurately performed. 

### 2. Implementation State of `calculate_aid`
The codebase (`daily-coin`) is largely built for querying and scoring cryptocurrency data from Binance. The only trace of the "financial aid" domain is an isolated `calculate-aid` Typer command in `main.py`.

**Current User Flow:**
- The user runs the CLI passing a file path: `calculate-aid <path_to_json>`.
- The application performs a basic file existence check.
- It parses the JSON file using `json.load`.
- It echoes the parsed JSON to the terminal.
- **Domain Logic Output:** It bypasses any actual logic or rule processing and statically outputs a dummy value: `Dummy aid calculation: $10,000`.

**Critique:**
- **Correctness:** The financial aid rules are completely unimplemented. The command acts only as a scaffold.
- **Validation:** There is no schema validation for the ingested JSON. Any valid JSON file is accepted, regardless of whether it actually constitutes a valid "student profile."

### 3. Separation of Concerns
The business logic that powers the legacy portion of the app (cryptocurrency portfolio selection) is correctly decoupled into `logic.py`, `history.py`, and `news.py`. If financial aid logic is to be properly integrated, a similar separation is needed (e.g., `aid_calculator.py`). Currently, the entirety of the `calculate-aid` execution context is contained within the `main.py` routing layer.

## Actionable Recommendations
1. **Define the Domain Context:** Update `docs/context.md` (or create a dedicated `docs/financial-aid-rules.md`) to explicitly document the financial aid formulas, student profile schema, and eligibility criteria.
2. **Implement Business Logic:** Replace the dummy `$10,000` return value in `main.py` with an actual rules engine.
3. **Data Validation:** Implement schema validation (e.g., using `pydantic`) for the incoming student profile JSON to ensure all required fields are present before calculating aid.
4. **Project Scope Realignment:** The project is experiencing an identity split between a "Daily Crypto Portfolio" and a "Financial Aid" tool. If this repository is pivoting entirely to financial aid, the legacy crypto logic, documentation, and dependencies (like `python-binance`) should be officially deprecated and removed to avoid confusion.
