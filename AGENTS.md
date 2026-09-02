# Agent Instructions

You are an AI coding agent assigned to build and maintain the `daily-coin` CLI.

**Follow this progressive disclosure map for context:**
1. **Domain & Rules:** Read `docs/context.md` to understand the portfolio generation rules and user flows.
2. **Technical Blueprint:** Read `docs/architecture.md` to understand the CLI framework and data models.
3. **Decisions:** Read `docs/decisions.md` to understand past architectural choices.
4. **Current State:** Read `progress.md` for the last session handoff.
5. **Next Task:** Run `gh issue list --state open` and pick **one** open GitHub issue. Markdown docs are the source of truth; issues are brief tickets that should link those docs.

**Session Rules:**
- Work one GitHub issue at a time.
- Create a branch named `issue-N-short-slug` from `main`. Do not commit ticket work directly to `main`.
- Open a pull request that includes `Closes #N`. Wait for CI (pytest + ruff) to pass.
- When finishing a session, update `progress.md` with short handoff notes (current status only; prune old session logs).
- Do not write implementation details in this file. Keep it as a short map/router.
- Always check for dead code and ensure documentation (like `progress.md`) is updated after making code changes.

**Quick Command Reference:**
- **Run the CLI Application:** `.\venv\Scripts\python.exe main.py run` (or `python main.py run` inside activated venv)
- **Run tests:** `.\venv\Scripts\python.exe -m pytest` (do NOT run raw `pytest` outside python wrapper, or import path errors will occur)
- **Lint:** `.\venv\Scripts\python.exe -m ruff check .`
- **Shortcut `/run`**: Run the app and print the portfolio (equivalent to `.\venv\Scripts\python.exe main.py run`).
- **Shortcut `/run-fe`**: Start both the backend API server (`.\venv\Scripts\python.exe main.py serve`) and frontend development server (`npm run dev` in the `frontend` directory), then print the application link in the chat.
- **Shortcut `/m&p`**: Commit, push, and open or update a pull request for the current ticket branch. Do not merge ticket work straight to `main`.
