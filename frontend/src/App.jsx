// App.jsx — room scene with a swappable background image. Each of the 21 fixed
// markers shows either a clue SPRITE (if a clue is placed there) or a pulsing
// placeholder dot (if not). STRUCTURE is fixed for every environment; only the
// background image changes (office / hospital / government).

import { useState, useEffect, useMemo } from 'react'
import { MARKERS } from './data/markers.js'
import { getClueArt } from './data/clueArtMap.js'
import { getScenario, GatekeeperClientError } from './api/gatekeeperClient.js'
import ClueDetailPanel from './ClueDetailPanel.jsx'
import Inventory from './Inventory.jsx'
import PersonaSelect from './PersonaSelect.jsx'
import GatekeeperCharacter from './GatekeeperCharacter.jsx'
import GatekeeperDialogue from './GatekeeperDialogue.jsx'
import './App.css'

// Maps the scenario's room_background value to an actual file in public/.
// Only 'office' is confirmed to match a real file below — add hospital/
// government once you've checked the exact filenames your Python actually
// emits and what's actually sitting in public/.
const BACKGROUND_FILES = {
  office: 'room-office.png',
  hospital: 'room-hospital.png',
  government: 'room-government.png',
}
const DEFAULT_BACKGROUND = 'room-office.png'

function resolveBackground(roomBackground) {
  const file = BACKGROUND_FILES[roomBackground]
  if (!file) {
    console.warn(
      `No background mapped for room_background "${roomBackground}" — falling back to office. ` +
      `Add the real filename to BACKGROUND_FILES once you know it.`
    )
    return DEFAULT_BACKGROUND
  }
  return file
}

// Fisher-Yates — scatters each session's clues across different markers
// rather than always landing on the same few positions. Markers that
// don't get a clue stay empty (pulsing dot) for now — misdirection/filler
// objects are a later addition per spec_patch_marker_system.md.
function shuffle(array) {
  const a = [...array]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

// scenario.clues[].properties comes back from the backend as an evidence
// object for the Python evidence-checker (e.g. { dated_today: true,
// signed_by: "..." }) — written for machine matching, not as player-facing
// bullets. This is a stop-gap humaniser so the detail panel shows
// *something* readable either way. See the note after this file about
// whether the scenario generator should instead write dedicated display
// bullets directly.
function humanizeProperties(properties) {
  if (Array.isArray(properties)) return properties
  if (properties && typeof properties === 'object') {
    return Object.entries(properties).map(([key, value]) => {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
      if (value === true) return label
      if (value === false) return `Not ${label}`
      return `${label}: ${value}`
    })
  }
  return []
}

function App() {
  const [turnsRemaining] = useState(15)
  const [selectedArtKey, setSelectedArtKey] = useState(null)
  const [examinedClues, setExaminedClues] = useState(() => new Set())
  const [persona, setPersona] = useState(null)
  const [talking, setTalking] = useState(false)

  const [scenario, setScenario] = useState(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)
  const [scenarioError, setScenarioError] = useState(null)

  // Gatekeeper character position, room-relative % — not part of MARKERS
  // since it isn't a clue. Eyeball these two numbers against your door's
  // actual position and adjust until it lines up.
  const GATEKEEPER_POSITION = { x: 46, y: 42 }

  function loadScenario(chosenPersona) {
    setScenarioLoading(true)
    setScenarioError(null)
    getScenario(chosenPersona)
      .then(setScenario)
      .catch((err) => {
        setScenarioError(
          err instanceof GatekeeperClientError
            ? err.message
            : 'Something went wrong generating the scenario.'
        )
      })
      .finally(() => setScenarioLoading(false))
  }

  // Fires once, right after a persona is chosen.
  useEffect(() => {
    if (persona) loadScenario(persona)
  }, [persona])

  const placedClues = useMemo(() => {
    if (!scenario) return {}
    const shuffledIds = shuffle(MARKERS.map((m) => m.id))
    const map = {}
    scenario.clues.forEach((clue, i) => {
      map[shuffledIds[i]] = clue.art_key
    })
    return map
  }, [scenario])

  const clueDetails = useMemo(() => {
    if (!scenario) return {}
    const map = {}
    scenario.clues.forEach((clue) => {
      map[clue.art_key] = {
        name: clue.name,
        description: clue.description,
        properties: humanizeProperties(clue.properties),
      }
    })
    return map
  }, [scenario])

  function handleExamine(artKey) {
    if (!artKey) return // empty/misdirection/filler markers — no content yet
    setSelectedArtKey(artKey)
    setExaminedClues((prev) => new Set(prev).add(artKey))
  }

  const selectedClue = selectedArtKey
    ? { art_key: selectedArtKey, ...clueDetails[selectedArtKey] }
    : null

  // -- Screen 1: no persona chosen yet --
  if (!persona) {
    return <PersonaSelect onSelect={setPersona} />
  }

  // -- Screen 2: scenario is generating --
  if (scenarioLoading || (!scenario && !scenarioError)) {
    return (
      <div className="persona-select">
        <div className="persona-select-inner">
          <h1 className="persona-select-title">THE GATEKEEPER</h1>
          <p className="persona-select-subtitle">Generating your scenario…</p>
        </div>
      </div>
    )
  }

  // -- Screen 3: scenario generation failed --
  if (scenarioError) {
    return (
      <div className="persona-select">
        <div className="persona-select-inner">
          <h1 className="persona-select-title">THE GATEKEEPER</h1>
          <p className="persona-select-subtitle">{scenarioError}</p>
          <button
            className="persona-card"
            style={{ maxWidth: 220, margin: '0 auto' }}
            onClick={() => loadScenario(persona)}
          >
            <span className="persona-card-name">Retry</span>
          </button>
        </div>
      </div>
    )
  }

  // -- Screen 4: the room --
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
            details={clueDetails}
            onSelect={handleExamine}
          />

          <div
            className="room"
            style={{ backgroundImage: `url(/${resolveBackground(scenario.room_background)})` }}
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

            <GatekeeperCharacter
              x={GATEKEEPER_POSITION.x}
              y={GATEKEEPER_POSITION.y}
              onClick={() => setTalking(true)}
            />
          </div>
        </div>
      </main>

      <footer className="statusbar">
        <span>Turns remaining: <strong>{turnsRemaining}</strong></span>
        <span className="statusbar-hint">
          {talking ? 'Type your response below.' : 'Click the Gatekeeper to speak.'}
        </span>
      </footer>

      <ClueDetailPanel clue={selectedClue} onClose={() => setSelectedArtKey(null)} />
      {talking && <GatekeeperDialogue onClose={() => setTalking(false)} />}
    </div>
  )
}

export default App