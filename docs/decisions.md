# Architecture Decision Records (ADR)

## 001 - Use of Explicit File Memory over Plugins
**Context:** We need a way for the AI agent to maintain long-term context across sessions.
**Decision:** We will use a deterministic, explicitly version-controlled file approach (`AGENTS.md`, `progress.md`, and the docs in `docs/`) instead of relying on implicit vector-database memory plugins.
**Consequences:** The agent will reliably orient itself on every initialization, but we must be disciplined in pruning `progress.md` to avoid context bloat. Work tracking moved from `tasks.json` to GitHub Issues in ADR 006.

## 002 - CLI Framework
**Context:** Need a fast, typed CLI framework.
**Decision:** Selected `Typer` over `argparse` or `Click`.
**Consequences:** Leverages Python type hints, saving boilerplate and generating automatic help menus.

## 003 - News Aggregation Approach
**Context:** Needed a way to aggregate crypto news without relying on discontinued or paid APIs.
**Decision:** Selected `feedparser` to directly read RSS feeds from major outlets (CoinDesk, Cointelegraph).
**Consequences:** 100% free and zero API keys required, but sources are hardcoded.

## 004 - Sentiment Analysis
**Context:** Needed to derive bullish/bearish intent from headlines to dynamically alter coin selection.
**Decision:** Selected `vaderSentiment` over `TextBlob` or heavier LLM integrations.
**Consequences:** VADER is perfectly tuned for short, social-media-style texts, requires zero external corporas/downloads, and keeps the CLI lightweight and offline-friendly.

## 005 - Local Docker workspace
**Context:** Cloud agents run the stack in a Linux VM with ports 8000/5173. Developers on Windows 11 need the same layout without duplicating cloud-only tooling.
**Decision:** Ship a single Compose service (`workspace`) built from a Python 3.12 + Node 22 image, bind-mount the repo, and publish both ports to the host. Optional Dev Containers reuse that service with `overrideCommand`.
**Consequences:** `docker compose up` on Docker Desktop matches the cloud `/run-fe` ports. File watching needs polling on Windows bind mounts. This is not a clone of Cursor Cloud MCP or the agent desktop.

## 006 - GitHub Issues and PRs over local task files
**Context:** The Antigravity `tasks.json` queue went stale (including leftover work from an unrelated CLI) and did not give humans a shared backlog or review gate.
**Decision:** Track work in GitHub Issues. Each ticket is a brief summary plus links to markdown docs (the source of truth). Land each ticket on a branch via a pull request. Keep `AGENTS.md` and `docs/` as the agent/product source of truth; keep `progress.md` as a short last-session handoff only.
**Consequences:** Agents pick one open issue (`gh issue list --state open`), branch as `issue-N-short-slug`, and open a PR that says `Closes #N`. CI (pytest + ruff) must pass before merge. Do not commit ticket work directly to `main`.
