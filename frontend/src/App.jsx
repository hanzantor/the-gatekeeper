// App.jsx — room scene with a swappable background image. Each of the 21 fixed
// markers shows either a clue SPRITE (if a clue is placed there) or a pulsing
// placeholder dot (if not). STRUCTURE is fixed for every environment; only the
// background image changes (office / hospital / government).
//
// KEYING NOTE: clues are keyed throughout by their scenario `id`, never by
// `art_key`. Several library clues deliberately share a sprite (the sprite set
// is smaller than the clue catalogue), so keying by art_key caused the second
// clue to overwrite the first — two markers showing the same sprite AND the
// same text. `id` is unique per clue; `art_key` is not.

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

const BACKGROUND_FILES = {
  office: 'room-office.png',
  hospital: 'room-hospital.png',
  government: 'room-government.png',
  research_lab: 'room-office.png', // no dedicated lab background yet
}
const DEFAULT_BACKGROUND = 'room-office.png'

function resolveBackground(roomBackground) {
  const file = BACKGROUND_FILES[roomBackground]
  if (!file) {
    console.warn(
      `No background mapped for room_background "${roomBackground}" — falling back to office.`
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

function App() {
  const [turnsRemaining] = useState(15)
  const [selectedClueId, setSelectedClueId] = useState(null)
  const [examinedClues, setExaminedClues] = useState(() => new Set())
  const [persona, setPersona] = useState(null)
  const [talking, setTalking] = useState(false)

  const [scenario, setScenario] = useState(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)
  const [scenarioError, setScenarioError] = useState(null)

  // Gatekeeper character position, room-relative %.
  const GATEKEEPER_POSITION = { x: 46, y: 42 }

  function loadScenario(chosenPersona) {
    setScenarioLoading(true)
    setScenarioError(null)
    // A new scenario means a new session — clear anything from the last one.
    setExaminedClues(new Set())
    setSelectedClueId(null)
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

  // markerId -> clue id. Keyed by clue id so two clues sharing a sprite
  // still occupy two distinct markers with their own content.
  const placedClues = useMemo(() => {
    if (!scenario) return {}
    const shuffledIds = shuffle(MARKERS.map((m) => m.id))
    const map = {}
    scenario.clues.forEach((clue, i) => {
      map[shuffledIds[i]] = clue.id
    })
    return map
  }, [scenario])

  // clue id -> full clue record for the detail panel and inventory.
  const clueDetails = useMemo(() => {
    if (!scenario) return {}
    const map = {}
    scenario.clues.forEach((clue) => {
      map[clue.id] = {
        id: clue.id,
        art_key: clue.art_key,
        name: clue.name,
        description: clue.description,
        detail_points: clue.detail_points ?? [],
      }
    })
    return map
  }, [scenario])

  function handleExamine(clueId) {
    if (!clueId) return // empty/misdirection/filler markers — no content yet
    setSelectedClueId(clueId)
    setExaminedClues((prev) => new Set(prev).add(clueId))
  }

  const selectedClue = selectedClueId ? clueDetails[selectedClueId] : null

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
              const clueId = placedClues[m.id]
              const clue = clueId ? clueDetails[clueId] : null
              const art = clue ? getClueArt(clue.art_key, m.surface) : null
              const examined = clueId && examinedClues.has(clueId)

              return (
                <button
                  key={m.id}
                  className={`clue-marker${examined ? ' clue-marker-examined' : ''}`}
                  style={{ left: `${m.x}%`, top: `${m.y}%` }}
                  data-zone={m.zone}
                  data-surface={m.surface}
                  onClick={() => handleExamine(clueId)}
                  aria-label={
                    clue ? `Examine ${clue.name}` : `Examine marker ${m.id} (${m.zone})`
                  }
                >
                  {art?.found ? (
                    <img
                      className="clue-sprite"
                      src={art.src}
                      alt={clue.name}
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

      <ClueDetailPanel clue={selectedClue} onClose={() => setSelectedClueId(null)} />
      {talking && <GatekeeperDialogue onClose={() => setTalking(false)} />}
    </div>
  )
}

export default App