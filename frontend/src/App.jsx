import { useState, useEffect } from 'react'
import './App.css'
import { generatePortfolio as requestPortfolio, getHistory, getSettings, saveSettings } from './api'

// Upper bound for the stable and volatile counts. Keep in step with
// PORTFOLIO_COUNT_MAX in constants.py, which the API enforces.
const COUNT_MAX = 50

// Parse a count input and keep it inside the range the API accepts.
function clampCount(value) {
  const parsed = parseInt(value, 10)
  if (Number.isNaN(parsed)) return 1
  return Math.min(COUNT_MAX, Math.max(1, parsed))
}

// Two decimals for magnitudes of 1 or more; below that, 4 significant digits so
// sub-cent coins (SHIB, PEPE) and their MACD values do not round to 0.
// Mirrors formatting.format_number on the CLI side.
function formatNumber(value) {
  if (!Number.isFinite(value) || value === 0 || Math.abs(value) >= 1) {
    return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return value.toLocaleString(undefined, {
    minimumSignificantDigits: 4,
    maximumSignificantDigits: 4,
  })
}

function newestFirst(records) {
  return [...records].sort((a, b) => b.timestamp - a.timestamp)
}

function App() {
  const [loading, setLoading] = useState(false)
  const [portfolio, setPortfolio] = useState([])
  const [news, setNews] = useState([])
  const [history, setHistory] = useState([])
  const [stableCount, setStableCount] = useState(3)
  const [volatileCount, setVolatileCount] = useState(6)
  const [error, setError] = useState(null)
  const [isMock, setIsMock] = useState(false)
  // Where the cards on screen came from: { saved: true } = latest history record
  const [portfolioInfo, setPortfolioInfo] = useState(null)
  // True until the first settings/history load settles. Controls stay disabled
  // meanwhile, so a late load cannot overwrite a run the user already started
  // and a run cannot save default counts over the stored settings.
  const [initializing, setInitializing] = useState(true)

  // Trigger portfolio generation. Only runs when the user asks for it: each run
  // evaluates pending records and appends a new one to history.
  const generatePortfolio = async () => {
    setLoading(true)
    setError(null)
    try {
      // 1. Save the counts. This is a partial update: settings the dashboard does
      // not show (variance_percentile) keep their stored value.
      await saveSettings({ stable_count: stableCount, volatile_count: volatileCount })

      // 2. Fetch the recommendations
      const data = await requestPortfolio(stableCount, volatileCount)
      if (data.error) {
        setError(data.error)
        setLoading(false)
        return
      }
      setPortfolio(data.portfolio || [])
      setIsMock(Boolean(data.mock))
      setPortfolioInfo({ saved: false, time: Date.now() })
      setNews(data.news || [])
      try {
        setHistory(newestFirst(await getHistory()))
      } catch (err) {
        console.error(err)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // On load, read settings and history only. The latest saved portfolio is shown
  // from history; nothing is generated until the button is pressed.
  useEffect(() => {
    let cancelled = false
    const init = async () => {
      const [settings, records] = await Promise.all([
        getSettings().catch((err) => {
          console.error(err)
          return null
        }),
        getHistory().catch((err) => {
          console.error(err)
          return []
        }),
      ])
      if (cancelled) return
      setInitializing(false)
      if (settings) {
        setStableCount(settings.stable_count)
        setVolatileCount(settings.volatile_count)
      }
      const sorted = newestFirst(records)
      setHistory(sorted)
      const latest = sorted[0]
      if (latest?.picks?.length) {
        setPortfolio(latest.picks)
        setIsMock(false)
        setPortfolioInfo({ saved: true, time: latest.timestamp * 1000 })
      }
    }
    init()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <h1 className="brand-title">Daily Coin</h1>
          <p className="brand-subtitle">Heuristic Multi-Factor Cryptocurrency Portfolio Generator</p>
        </div>
        
        <div className="controls-section">
          <div className="settings-group">
            <label htmlFor="stable-input">Stable:</label>
            <input 
              id="stable-input"
              type="number" 
              min="1" 
              max={COUNT_MAX}
              value={stableCount}
              onChange={(e) => setStableCount(clampCount(e.target.value))}
              disabled={initializing}
              className="settings-input"
            />
            <label htmlFor="volatile-input">Volatile:</label>
            <input 
              id="volatile-input"
              type="number" 
              min="1" 
              max={COUNT_MAX}
              value={volatileCount}
              onChange={(e) => setVolatileCount(clampCount(e.target.value))}
              disabled={initializing}
              className="settings-input"
            />
          </div>
          <button 
            onClick={generatePortfolio} 
            disabled={loading || initializing}
            className="btn-primary"
          >
            {loading ? 'Rebalancing...' : initializing ? 'Loading...' : 'Run Portfolio Generator'}
          </button>
        </div>
      </header>

      {error && (
        <div className="error-notice" role="alert">
          Error: {error}
        </div>
      )}

      {/* Tied to the cards on screen, so it stays up if a later request fails */}
      {isMock && portfolio.length > 0 && (
        <div className="mock-notice" role="status">
          Binance is unavailable: these picks use mock market data. They are placeholders,
          were not saved to history, and past picks were not evaluated.
        </div>
      )}

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Left Side: Current Recommendations */}
        <div className="dashboard-column">
          <section className="glass-panel">
            <div className="panel-content">
              <h2 className="panel-title">
                Recommended Allocation
                {portfolio.length > 0 && (
                  <span className="panel-subtitle">
                    {portfolio.filter(p => p.type === 'Stable').length} Stable / {portfolio.filter(p => p.type === 'Volatile').length} Volatile
                    {portfolioInfo && (
                      <>
                        {' · '}
                        {portfolioInfo.saved ? 'Last saved run, entry prices from ' : 'Generated '}
                        {new Date(portfolioInfo.time).toLocaleString()}
                      </>
                    )}
                  </span>
                )}
              </h2>
              
              {loading ? (
                <div className="loading-spinner">
                  <div className="spinner"></div>
                  <p>Fetching market data, executing technical analysis & evaluating sentiment...</p>
                </div>
              ) : portfolio.length === 0 ? (
                <div className="empty-state">
                  No saved portfolio yet. Click "Run Portfolio Generator" above to create one.
                </div>
              ) : (
                <div className="portfolio-grid">
                  {portfolio.map((coin) => (
                    <div key={coin.coin} className="coin-card">
                      <div className="coin-card-header">
                        <span className="coin-symbol">{coin.display_name}</span>
                        <span className={`coin-badge ${coin.type.toLowerCase()}`}>
                          {coin.type}
                        </span>
                      </div>
                      <div className="coin-price">
                        ${formatNumber(coin.price)}
                      </div>
                      <div className="coin-metrics">
                        <div className="metric-item">
                          <span className="metric-label">Score</span>
                          <span className="metric-value highlight">{coin.score.toFixed(2)}</span>
                        </div>
                        <div className="metric-item">
                          <span className="metric-label">RSI (14)</span>
                          <span className="metric-value">{coin.rsi.toFixed(1)}</span>
                        </div>
                        {coin.explanation && (
                          <div className="metric-item">
                            <span className="metric-label">MACD</span>
                            <span className="metric-value">
                              {formatNumber(coin.explanation.macd)} / {formatNumber(coin.explanation.signal)}
                            </span>
                          </div>
                        )}
                      </div>
                      {coin.explanation?.summary && (
                        <p className="coin-explanation">{coin.explanation.summary}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* Past Performance / Logs */}
          <section className="glass-panel">
            <div className="panel-content">
              <h2 className="panel-title">Historical Portfolios & Evaluation</h2>
              <div className="history-list">
                {history.length === 0 ? (
                  <div className="empty-state">No past evaluations recorded yet.</div>
                ) : (
                  history.map((record, index) => {
                    const date = new Date(record.timestamp * 1000).toLocaleString()
                    return (
                      <div key={index} className="history-card">
                        <div className="history-header">
                          <span>Portfolio Generated at {date}</span>
                          <span className="history-status">
                            {record.evaluated ? 'Evaluated' : 'Pending Evaluation'}
                          </span>
                        </div>
                        <div className="history-picks">
                          {record.portfolio.map((coin) => {
                            const performance = record.performance?.[coin]
                            return (
                              <div key={coin} className="pick-pill">
                                <span>{coin.replace('USDT', '')}</span>
                                {performance !== undefined && (
                                  <span className={`gain-indicator ${performance >= 0 ? 'up' : 'down'}`}>
                                    {performance >= 0 ? '+' : ''}{(performance * 100).toFixed(2)}%
                                  </span>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          </section>
        </div>

        {/* Right Side: News Sentiment Hub */}
        <section className="glass-panel">
          <div className="panel-content">
            <h2 className="panel-title">Crypto News & VADER Sentiment</h2>
            <div className="news-list">
              {news.length === 0 ? (
                <div className="empty-state">No news parsed yet. Click "Run Portfolio Generator" to pull the RSS feed.</div>
              ) : (
                news.map((item, index) => (
                  <div key={index} className="news-item">
                    <a href={item.link} target="_blank" rel="noopener noreferrer" className="news-title">
                      {item.title}
                    </a>
                    <div className="news-meta">
                      <span>Source: {item.source}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

export default App
