import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [loading, setLoading] = useState(false)
  const [portfolio, setPortfolio] = useState([])
  const [news, setNews] = useState([])
  const [history, setHistory] = useState([])
  const [stableCount, setStableCount] = useState(3)
  const [volatileCount, setVolatileCount] = useState(6)
  const [error, setError] = useState(null)

  const API_BASE = 'http://127.0.0.1:8000/api'

  // Fetch settings on mount
  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/settings`)
      if (!res.ok) throw new Error('Failed to fetch settings')
      const data = await res.json()
      setStableCount(data.stable_count)
      setVolatileCount(data.volatile_count)
      return data
    } catch (err) {
      console.error(err)
      return { stable_count: 3, volatile_count: 6 }
    }
  }

  // Fetch history list
  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history`)
      if (!res.ok) throw new Error('Failed to fetch history')
      const data = await res.json()
      setHistory(data.sort((a, b) => b.timestamp - a.timestamp))
    } catch (err) {
      console.error(err)
    }
  }

  // Trigger portfolio generation
  const generatePortfolio = async () => {
    setLoading(true)
    setError(null)
    try {
      // 1. Save settings to the server
      await fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stable_count: stableCount, volatile_count: volatileCount })
      })

      // 2. Fetch the recommendations
      const res = await fetch(`${API_BASE}/portfolio/generate?stable=${stableCount}&volatile=${volatileCount}`)
      if (!res.ok) throw new Error('Failed to generate portfolio. Make sure backend is running.')
      const data = await res.json()
      if (data.error) {
        setError(data.error)
        setLoading(false)
        return
      }
      setPortfolio(data.portfolio || [])
      setNews(data.news || [])
      await fetchHistory()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const init = async () => {
      await fetchSettings()
      await fetchHistory()
      generatePortfolio()
    }
    init()
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
              max="10"
              value={stableCount}
              onChange={(e) => setStableCount(parseInt(e.target.value) || 1)}
              className="settings-input"
            />
            <label htmlFor="volatile-input">Volatile:</label>
            <input 
              id="volatile-input"
              type="number" 
              min="1" 
              max="20"
              value={volatileCount}
              onChange={(e) => setVolatileCount(parseInt(e.target.value) || 1)}
              className="settings-input"
            />
          </div>
          <button 
            onClick={generatePortfolio} 
            disabled={loading}
            className="btn-primary"
          >
            {loading ? 'Rebalancing...' : 'Run Portfolio Generator'}
          </button>
        </div>
      </header>

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#f87171',
          padding: '16px',
          borderRadius: '12px',
          fontWeight: '500'
        }}>
          Error: {error}
        </div>
      )}

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Left Side: Current Recommendations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
          <section className="glass-panel">
            <div className="panel-content">
              <h2 className="panel-title">
                Recommended Allocation
                {portfolio.length > 0 && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {portfolio.filter(p => p.type === 'Stable').length} Stable / {portfolio.filter(p => p.type === 'Volatile').length} Volatile
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
                  No portfolio generated yet. Click "Run Portfolio Generator" above.
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
                        ${coin.price > 1 ? coin.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : coin.price.toFixed(4)}
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
                      </div>
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
                          <span style={{ fontWeight: '600' }}>
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
