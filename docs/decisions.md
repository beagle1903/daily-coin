# Architecture Decision Records (ADR)

## 001 - Use of Explicit File Memory over Plugins
**Context:** We need a way for the AI agent to maintain long-term context across sessions.
**Decision:** We will use a deterministic, explicitly version-controlled file approach (`AGENTS.md`, `tasks.json`, `progress.md`) instead of relying on implicit vector-database memory plugins.
**Consequences:** The agent will reliably orient itself on every initialization, but we must be disciplined in pruning `progress.md` to avoid context bloat.

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
