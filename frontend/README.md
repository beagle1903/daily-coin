# Daily Coin dashboard

Vite + React single-page app for the Daily Coin API. The whole UI is in `src/App.jsx`.

```bash
npm install
npm run dev     # http://localhost:5173
npm run lint    # oxlint
npm run build
```

The dashboard calls the API at `http://127.0.0.1:8000/api`, so start it first with `python main.py serve --reload` from the repository root. Set `VITE_DAILY_COIN_API_KEY` to the same value as the API's `DAILY_COIN_API_KEY`.

Setup, the API key model and the Docker workflow are described in the [root README](../README.md).
