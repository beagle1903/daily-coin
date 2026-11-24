---
name: run-fe
description: Start the daily-coin API server and the dashboard dev server, then print the dashboard link. Use when asked to run the frontend, the dashboard, or the web app.
---
# Start the API and the dashboard

Start both servers as background processes so the session is not blocked, then give the user the link.

1. **API** (repo root, venv interpreter; a bare `python` can hit import errors on Windows):
   - PowerShell: `.\venv\Scripts\python.exe main.py serve`
   - Git Bash on Windows: `./venv/Scripts/python.exe main.py serve`
   - Linux or macOS: `./venv/bin/python main.py serve`
2. **Dashboard**: `npm run dev` with `frontend/` as the working directory (run `npm ci` there first if `frontend/node_modules` is missing).
3. Wait until the API answers on port 8000 and Vite reports its URL, then print the dashboard link (normally http://localhost:5173) in your reply.

The dashboard needs the same value in `DAILY_COIN_API_KEY` and `VITE_DAILY_COIN_API_KEY` in `.env`; if API calls come back 401, say so.
