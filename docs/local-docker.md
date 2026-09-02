# Local workspace on Windows 11 + Docker Desktop

This matches the cloud agent layout: one Linux container with Python 3.12, Node 22, the repo at `/workspace`, the API on port **8000**, and Vite on port **5173**. Docker Desktop publishes those ports to `localhost` on Windows (the same idea as Cursor’s cloud port tunnel).

## Prerequisites

- [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) with the **WSL 2** engine enabled
- Git

Clone the repo on the Linux filesystem when you can (`\\wsl$\Ubuntu\home\...`). Bind mounts from `C:\` work, but file watching is slower.

## Run the app (PowerShell)

```powershell
cd path\to\daily-coin
copy .env.example .env   # optional; add Binance keys and DAILY_COIN_API_KEY / VITE_DAILY_COIN_API_KEY
docker compose up --build
```

Then open:

- Frontend: [http://localhost:5173](http://localhost:5173)
- API: [http://localhost:8000/docs](http://localhost:8000/docs)

Stop with `Ctrl+C`, or `docker compose down`.

The UI calls `http://127.0.0.1:8000/api` from your browser and sends `X-API-Key` from `VITE_DAILY_COIN_API_KEY`. Set the same value as `DAILY_COIN_API_KEY` in `.env` so the API accepts dashboard requests. Compose passes `VITE_DAILY_COIN_API_KEY` from that host file (falling back to `DAILY_COIN_API_KEY` if unset).

## CLI inside the container

```powershell
docker compose run --rm workspace python main.py run
docker compose run --rm workspace python -m pytest
```

Or attach to a running stack:

```powershell
docker compose exec workspace python main.py run
```

## Cursor / VS Code Dev Container

1. Open the repo folder in Cursor.
2. Command Palette → **Dev Containers: Reopen in Container**.
3. In the container terminal: `python main.py serve --host 0.0.0.0 --port 8000` and, in `frontend`, `npm run dev -- --host 0.0.0.0 --port 5173`.

Dev Containers override the Compose `command`, so servers do not start automatically. That keeps a cloud-agent-style shell instead of tying the container to Vite.

## What is not copied from the cloud VM

- Cursor Cloud MCP and the agent desktop
- Automatic Binance access (geo blocks still apply; the app falls back to mock market data)
- Your local `.env` (keep secrets on the host; set `DAILY_COIN_API_KEY` and `VITE_DAILY_COIN_API_KEY` for the dashboard)
