# Architecture Decision Records (ADR)

## 001 - Use of Explicit File Memory over Plugins
**Context:** We need a way for the AI agent to maintain long-term context across sessions.
**Decision:** We will use a deterministic, explicitly version-controlled file approach (`AGENTS.md`, `tasks.json`, `progress.md`) instead of relying on implicit vector-database memory plugins.
**Consequences:** The agent will reliably orient itself on every initialization, but we must be disciplined in pruning `progress.md` to avoid context bloat.

## 002 - CLI Framework
**Context:** Need a fast, typed CLI framework.
**Decision:** Selected `Typer` over `argparse` or `Click`.
**Consequences:** Leverages Python type hints, saving boilerplate and generating automatic help menus.
