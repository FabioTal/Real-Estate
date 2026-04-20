import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

const QUICK_SEARCHES = [
  "Apartament 2+1 Tiranë",
  "Shtepi me qera Durres",
  "Vila shitje Albania",
  "Apartament nen 100k euro",
  "Garsoniere Tirane qera",
]

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: 'Mirë se vini! Unë jam agjenti juaj i pronave në Shqipëri. 🏠\n\nMund të më shkruani gjëra si:\n• "Gjej apartament 2+1 në Tiranë"\n• "Kërko shtëpi nën 100,000 euro"\n• "Shfaq pronat e fundit"\n\nJam gati t\'ju ndihmoj!',
  listings: []
}

const openLink = (url) => {
  if (!url || !url.startsWith('http')) return
  const a = document.createElement('a')
  a.href = url
  a.target = '_blank'
  a.rel = 'noopener noreferrer'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState({ total: 0, merrjep: 0, njoftime: 0, instagram: 0 })
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchStats = async () => {
    try {
      const res = await axios.get('http://localhost:8000/stats')
      setStats(res.data)
    } catch (e) {}
  }

  const sendMessage = async (text) => {
    const userText = text || input.trim()
    if (!userText || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userText }])
    setLoading(true)

    try {
      const res = await axios.post('http://localhost:8000/chat', { message: userText })
      const data = res.data

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply + (data.result ? '\n\n' + data.result : ''),
        listings: data.listings || []
      }])

      fetchStats()
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Gabim në lidhje me serverin. Sigurohuni që backend është duke punuar.',
        listings: []
      }])
    }

    setLoading(false)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const cleanLocation = (loc) => {
    if (!loc) return ''
    const bad = ['Pallati', 'Rruga', 'Njësia', 'Koordinata', 'Vendndodhja',
      'Adresa', 'Apliko', 'Anulo', 'zgjedhur', 'Bashkiake']
    if (bad.some(k => loc.includes(k)) || loc.length > 40) {
      const l = loc.toLowerCase()
      if (l.includes('tiranë') || l.includes('tirane')) return 'Tiranë'
      if (l.includes('durrës') || l.includes('durres')) return 'Durrës'
      if (l.includes('vlorë') || l.includes('vlore')) return 'Vlorë'
      if (l.includes('shkodër') || l.includes('shkoder')) return 'Shkodër'
      return 'Albania'
    }
    return loc
  }

  return (
    <div className="app">
      <div className="sidebar">
        <div className="sidebar-logo">
          <h1>🏠 Property Agent</h1>
          <p>Albania Real Estate AI</p>
        </div>

        <div className="sidebar-stats">
          <div className="stat-item">
            <span className="stat-label">Total listings</span>
            <span className="stat-value">{stats.total}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">MerrJep</span>
            <span className="stat-value">{stats.merrjep}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Njoftime</span>
            <span className="stat-value">{stats.njoftime}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Instagram</span>
            <span className="stat-value">{stats.instagram}</span>
          </div>
        </div>

        <div className="sidebar-sources">
          <h3>Sources</h3>
          <div className="source-item active">
            <div className="source-dot" style={{background:'#4ade80'}}></div>
            MerrJep.al
          </div>
          <div className="source-item active">
            <div className="source-dot" style={{background:'#4ade80'}}></div>
            Njoftime.com
          </div>
          <div className="source-item active">
            <div className="source-dot" style={{background:'#e879f9'}}></div>
            Instagram
          </div>
          <div className="source-item">
            <div className="source-dot" style={{background:'#333'}}></div>
            Facebook (soon)
          </div>
        </div>

        <div className="quick-searches">
          <h3>Quick searches</h3>
          {QUICK_SEARCHES.map((q, i) => (
            <button key={i} className="quick-btn" onClick={() => sendMessage(q)}>
              🔍 {q}
            </button>
          ))}
        </div>
      </div>

      <div className="chat-area">
        <div className="chat-header">
          <div>
            <h2><span className="status-dot"></span>Property AI Agent</h2>
            <p>Searching MerrJep, Njoftime, Instagram in real-time</p>
          </div>
          <div style={{fontSize:'12px', color:'#555'}}>
            Updates every 15 min
          </div>
        </div>

        <div className="messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div>
                <div className="bubble">
                  {msg.content}
                </div>
                {msg.listings && msg.listings.length > 0 && (
                  <div className="property-cards">
                    {msg.listings.map((l, j) => (
                      <div
                        key={j}
                        className="property-card"
                        onClick={() => openLink(l[9])}
                        title="Click to open listing"
                      >
                        <div className="card-title">{l[3]}</div>
                        <div className="card-meta">
                          {l[4] && l[4] !== 'No price' && (
                            <span className="card-price">{l[4]}</span>
                          )}
                          {cleanLocation(l[5]) && (
                            <span className="card-location">
                              📍 {cleanLocation(l[5])}
                            </span>
                          )}
                          <span className="card-source">{l[1]}</span>
                        </div>
                        {l[9] && (
                          <div style={{
                            fontSize: '11px',
                            color: '#4ade80',
                            marginTop: '6px',
                            wordBreak: 'break-all'
                          }}>
                            🔗 {l[9].substring(0, 60)}...
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="avatar">🤖</div>
              <div className="bubble">
                <div className="typing">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <textarea
            className="input-box"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Shkruani kërkesën tuaj... (p.sh. 'Gjej apartament 2+1 në Tiranë')"
            rows={1}
          />
          <button
            className="send-btn"
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  )
}
