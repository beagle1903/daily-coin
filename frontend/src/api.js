// API client. Paths are relative to the page origin: the Vite dev server proxies
// /api to the backend (see vite.config.js), so no host or port is hard-coded.
// Set VITE_API_BASE to call a backend directly instead (it must allow CORS).
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

function apiHeaders(extra = {}) {
  return {
    'X-API-Key': import.meta.env.VITE_DAILY_COIN_API_KEY || '',
    ...extra,
  }
}

function errorMessageForStatus(status, fallback) {
  if (status === 401) return 'Unauthorized: missing or invalid API key.'
  if (status === 429) return 'Too many portfolio requests. Try again in a minute.'
  return fallback
}

// A 502 carries the upstream failure in `detail` (for example Binance being
// unavailable); show it instead of the generic message.
async function errorMessageForResponse(res, fallback) {
  if (res.status === 502) {
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') return body.detail
    } catch {
      // not JSON: fall through to the generic message
    }
  }
  return errorMessageForStatus(res.status, fallback)
}

async function request(path, options, fallbackMessage) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: apiHeaders(options.headers),
  })
  if (!res.ok) {
    throw new Error(await errorMessageForResponse(res, fallbackMessage))
  }
  return res.json()
}

export function getSettings() {
  return request('/settings', {}, 'Failed to fetch settings')
}

export function getHistory() {
  return request('/history', {}, 'Failed to fetch history')
}

// Partial update: settings the dashboard does not send keep their stored value.
export function saveSettings(settings) {
  return request(
    '/settings',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    },
    'Failed to save settings',
  )
}

export function generatePortfolio(stable, volatile) {
  return request(
    `/portfolio/generate?stable=${stable}&volatile=${volatile}`,
    { method: 'POST' },
    'Failed to generate portfolio. Make sure backend is running.',
  )
}
