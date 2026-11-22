# Agent Instructions

You are an AI coding agent assigned to build and maintain `daily-coin`: a Python CLI, a FastAPI backend and a React dashboard.

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

**Commands:** See the [README](README.md); it is the only command reference. On Windows use `.\venv\Scripts\python.exe -m pytest` rather than a bare `pytest`.

**Shortcuts** (skills in `.agents/skills/`):
- **`/run`**: Run the CLI and print the portfolio.
- **`/run-cli`**: Run the CLI and show the results (past performance, sentiment, new portfolio). Lives in `.claude/skills/run-cli/` for Claude Code.
- **`/run-fe`**: Start the API and the dashboard dev server, then print the dashboard link.
- **`/m&p`**: Commit, push, and open or update a pull request for the current ticket branch. Do not merge ticket work straight to `main`.
