# Architecture Blueprint

## System Overview
- **Language:** Python 3.10+
- **CLI Framework:** Typer (with Rich for terminal formatting)
- **Data Validation:** Pydantic for defining student data schemas.

## Project Structure
- `main.py`: Entry point for the Typer app.
- `models/`: Pydantic models for data validation.
- `calculations/`: Pure functions containing financial aid domain logic.
- `tests/`: Pytest suite for calculations and CLI commands.

## Design Patterns
- Separation of Concerns: CLI routing (in `main.py`) must be completely separate from calculation logic (in `calculations/`).
