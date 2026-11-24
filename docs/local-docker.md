# Local workspace on Windows 11 + Docker Desktop

This matches the cloud agent layout: one Linux container with Python 3.12, Node 22, the repo at `/workspace`, the API on port **8000**, and Vite on port **5173**. Docker Desktop publishes those ports to `localhost` on Windows.

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

The UI calls relative `/api` paths; the Vite dev server proxies them to `http://127.0.0.1:8000` (override with `DAILY_COIN_API_TARGET`, or call a backend directly with `VITE_API_BASE`, which needs CORS). It sends `X-API-Key` from `VITE_DAILY_COIN_API_KEY`. Set the same value as `DAILY_COIN_API_KEY` in `.env` so the API accepts dashboard requests. Compose passes `VITE_DAILY_COIN_API_KEY` from that host file (falling back to `DAILY_COIN_API_KEY` if unset). Anyone who can open the dashboard can read that key from the client bundle; it is not a per-user secret.

## CLI inside the container

```powershell
docker compose run --rm workspace python main.py run
docker compose run --rm workspace python -m pytest
```

Or attach to a running stack:

```powershell
docker compose exec workspace python main.py run
```

## VS Code Dev Container

1. Open the repo folder in VS Code (Dev Containers extension).
2. Command Palette → **Dev Containers: Reopen in Container**.
3. In the container terminal: `python main.py serve --host 0.0.0.0 --port 8000` and, in `frontend`, `npm run dev -- --host 0.0.0.0 --port 5173`.

Dev Containers override the Compose `command`, so servers do not start automatically. That keeps a cloud-agent-style shell instead of tying the container to Vite.

## What is not copied from the cloud VM

- Automatic Binance access (geo blocks still apply; the app falls back to mock market data)
- Your local `.env` (keep secrets on the host; set `DAILY_COIN_API_KEY` and `VITE_DAILY_COIN_API_KEY` for the dashboard)
