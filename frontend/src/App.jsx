// App.jsx — room scene with a swappable background image. Each of the 21 fixed
// markers shows either a clue SPRITE (if a clue is placed there) or a pulsing
// placeholder dot (if not). STRUCTURE is fixed for every environment; only the
// background image changes (office / hospital / government).

import { useState } from 'react'
import { MARKERS } from './data/markers.js'
import { getClueArt } from './data/clueArtMap.js'
import ClueDetailPanel from './ClueDetailPanel.jsx'
import Inventory from './Inventory.jsx'
import './App.css'

// TEST STUB: clue content, shaped exactly like the objects the real
// /api/scenario response will send (the_gatekeeper_spec.md §5). When
// Scenario Loading (Phase 3) wires in the live call, this object is
// replaced by scenario.clues — ClueDetailPanel needs no changes, since it
// only ever reads { art_key, name, description, properties }.
const CLUE_DETAILS = {
  storage_box: {
    name: 'Storage Box',
    description: 'A plain closed box with a fitted lid.',
    properties: ['Sealed shut', 'No visible label', 'Sits on the shelf'],
  },
  document_folder: {
    name: 'Document Folder',
    description: 'A folded cardboard folder, unlabelled.',
    properties: ['Contains a few loose papers', 'No name or date visible'],
  },
  access_badge: {
    name: 'Access Badge',
    description: 'A plastic ID badge on a clip, worn but legible.',
    properties: ['No photo', 'Clip still functional', "Today's date printed"],
  },
}

function App() {
  const [turnsRemaining] = useState(15)
  const [selectedArtKey, setSelectedArtKey] = useState(null)
  const [examinedClues, setExaminedClues] = useState(() => new Set())

  // Which environment background to show. Later the scenario picks this.
  const roomBackground = 'room-office.png'

  // TEST STUB: which clue sits on which marker id.
  // Hand-edit this to try sprites out. Later the scenario loader fills it in.
  // marker id -> clue art_key (must exist in CLUE_META in clueArtMap.js)
  const placedClues = {
    0:  'storage_box',        // shelf_left
    1:  'document_folder',    // shelf_right (mirrored)
    16: 'access_badge',
  }

  function handleExamine(artKey) {
    if (!artKey) return // empty/misdirection/filler markers — no content yet
    setSelectedArtKey(artKey)
    setExaminedClues((prev) => new Set(prev).add(artKey))
  }

  const selectedClue = selectedArtKey
    ? { art_key: selectedArtKey, ...CLUE_DETAILS[selectedArtKey] }
    : null

  return (
    <div className="app">
      <header className="titlebar">
        <span className="titlebar-name">THE GATEKEEPER</span>
        <span className="titlebar-status">SECURE ROOM · LOCKED</span>
      </header>

      <main className="stage">
        <div className="scene-row">
          <Inventory
            examinedKeys={[...examinedClues]}
            details={CLUE_DETAILS}
            onSelect={handleExamine}
          />

          <div
            className="room"
            style={{ backgroundImage: `url(/${roomBackground})` }}
          >
            {MARKERS.map((m) => {
              const artKey = placedClues[m.id]
              const art = artKey ? getClueArt(artKey, m.surface) : null
              const examined = artKey && examinedClues.has(artKey)

              return (
                <button
                  key={m.id}
                  className={`clue-marker${examined ? ' clue-marker-examined' : ''}`}
                  style={{ left: `${m.x}%`, top: `${m.y}%` }}
                  data-zone={m.zone}
                  data-surface={m.surface}
                  onClick={() => handleExamine(artKey)}
                  aria-label={
                    artKey ? `Examine ${artKey}` : `Examine marker ${m.id} (${m.zone})`
                  }
                >
                  {art?.found ? (
                    <img
                      className="clue-sprite"
                      src={art.src}
                      alt={artKey}
                      style={art.style}
                    />
                  ) : (
                    <span className="clue-dot" />
                  )}
                </button>
              )
            })}
          </div>
        </div>

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

      <ClueDetailPanel clue={selectedClue} onClose={() => setSelectedArtKey(null)} />
    </div>
  )
}

export default App