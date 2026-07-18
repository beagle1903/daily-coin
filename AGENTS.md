# Agent Instructions

You are an AI coding agent assigned to build and maintain the `daily-coin` CLI. 

**Follow this progressive disclosure map for context:**
1. **Domain & Rules:** Read `docs/context.md` to understand the portfolio generation rules and user flows.
2. **Technical Blueprint:** Read `docs/architecture.md` to understand the CLI framework and data models.
3. **Decisions:** Read `docs/decisions.md` to understand past architectural choices.
4. **Current State:** Read `progress.md` to see what was done in the last session.
5. **Next Task:** Check `tasks.json` to find your current assignment. Pick only ONE incomplete task.

**Session Rules:**
- DO NOT overwrite or delete items in `tasks.json`. Only change status from `incomplete` to `complete`.
- When finishing a session, update `progress.md` with handoff notes.
- Do not write implementation details in this file. Keep it as a short map/router.
- Always check for dead code and ensure documentation (like `progress.md`) is updated after making code changes.

**Quick Command Reference:**
- **Run the CLI Application:** `.\venv\Scripts\python.exe main.py run` (or `python main.py run` inside activated venv)
- **Run tests:** `.\venv\Scripts\python.exe -m pytest` (do NOT run raw `pytest` outside python wrapper, or import path errors will occur)
- **Shortcut `/run`**: Run the app and print the portfolio (equivalent to `.\venv\Scripts\python.exe main.py run`).
- **Shortcut `/run-fe`**: Start both the backend API server (`.\venv\Scripts\python.exe main.py serve`) and frontend development server (`npm run dev` in the `frontend` directory), then print the application link in the chat.
- **Shortcut `/m&p`**: Merge to main, commit, and push if any of them are needed.

