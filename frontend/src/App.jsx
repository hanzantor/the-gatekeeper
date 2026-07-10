// App.jsx — room scene with a swappable background image and glowing clue
// markers positioned on top. STRUCTURE is fixed for every environment; only
// the background image changes (office / hospital / government).
// The glowing dots are placeholders — Phase 7 art replaces them in the same spots.

import { useState } from 'react'
import { MARKERS } from './data/markers.js'
import './App.css'

function App() {
  const [turnsRemaining] = useState(15)

  // Which environment background to show. Later the scenario picks this.
  // Files live in /public: room-office.png, room-hospital.png, room-government.png
  const roomBackground = 'room-office.png'

  return (
    <div className="app">
      <header className="titlebar">
        <span className="titlebar-name">THE GATEKEEPER</span>
        <span className="titlebar-status">SECURE ROOM · LOCKED</span>
      </header>

      <main className="stage">
        {/* Room scene: background image + 21 fixed markers on top.
            Marker x/y come from data/markers.js and are the SAME across every
            environment — only the image behind them changes. */}
        <div
          className="room"
          style={{ backgroundImage: `url(/${roomBackground})` }}
        >
          {MARKERS.map((m) => (
            <button
              key={m.id}
              className="clue-marker"
              style={{ left: `${m.x}%`, top: `${m.y}%` }}
              data-zone={m.zone}
              data-surface={m.surface}
              aria-label={`Examine marker ${m.id} (${m.zone})`}
            >
              <span className="clue-dot" />
            </button>
          ))}
        </div>

        {/* Terminal */}
        <section className="terminal">
          <div className="terminal-header">
            <span className="terminal-dot" />
            GATEKEEPER TERMINAL
          </div>
          <div className="terminal-body">
            <p className="gatekeeper-line">
              State your business. The door does not open for those who cannot explain themselves.
            </p>
          </div>
          <div className="terminal-input">
            <input type="text" placeholder="Type your response…" className="terminal-field" />
            <button className="terminal-send">SEND</button>
          </div>
        </section>
      </main>

      <footer className="statusbar">
        <span>Turns remaining: <strong>{turnsRemaining}</strong></span>
        <span className="statusbar-hint">Examine the room. Make your case.</span>
      </footer>
    </div>
  )
}

export default App