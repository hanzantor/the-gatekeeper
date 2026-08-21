// App.jsx — room scene with a swappable background image. Each of the 21 fixed
// markers shows a clue SPRITE if (and only if) a clue is placed there. Empty
// markers render nothing at all and are non-interactive — no dot, no hover, no
// click target — so the player must genuinely search the room rather than
// "click the glowing things" (spec §7 / session log §9).
//
// App.jsx is the TURN OWNER. It holds the conversation history, the turn
// counter, and the game state, assembles the full game-state payload each
// turn, calls sendTurn(), and reads decision_type to drive the end states.
//
// KEYING NOTE: clues are keyed throughout by their scenario `id`, never by
// `art_key`. Several library clues deliberately share a sprite (the sprite set
// is smaller than the clue catalogue), so keying by art_key caused the second
// clue to overwrite the first — two markers showing the same sprite AND the
// same text. `id` is unique per clue; `art_key` is not.

import { useState, useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { MARKERS } from './data/markers.js'
import { getClueArt } from './data/clueArtMap.js'
import { getScenario, sendTurn, GatekeeperClientError } from './api/gatekeeperClient.js'
import ClueDetailPanel from './ClueDetailPanel.jsx'
import Inventory from './Inventory.jsx'
import PersonaSelect from './PersonaSelect.jsx'
import GatekeeperCharacter from './GatekeeperCharacter.jsx'
import GatekeeperDialogue from './GatekeeperDialogue.jsx'
import './App.css'

const TURN_LIMIT = 15

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
// rather than always landing on the same few positions. Markers that don't
// get a clue stay empty and are not rendered as interactive at all.
function shuffle(array) {
  const a = [...array]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function App() {
  const [selectedClueId, setSelectedClueId] = useState(null)
  const [examinedClues, setExaminedClues] = useState(() => new Set())
  const [persona, setPersona] = useState(null)
  const [talking, setTalking] = useState(false)

  // Pre-game briefing overlay. Shows the player's role, cover story and the
  // accusation before play begins. Starts open on every new scenario, and can
  // be re-opened mid-game from the status bar.
  const [briefingOpen, setBriefingOpen] = useState(true)

  const [scenario, setScenario] = useState(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)
  const [scenarioError, setScenarioError] = useState(null)

  // ── Turn-loop state (App.jsx owns the dialogue) ──────────────
  const [turnsRemaining, setTurnsRemaining] = useState(TURN_LIMIT)
  const [history, setHistory] = useState([])       // [{ role, text }]
  const [gkBusy, setGkBusy] = useState(false)       // waiting on the model
  const [gkError, setGkError] = useState(null)      // last turn's error, if any
  // outcome: null (ongoing) | 'ESCAPE' | 'LOCKED'
  const [outcome, setOutcome] = useState(null)

  // Gatekeeper character position, room-relative %.
  const GATEKEEPER_POSITION = { x: 46, y: 42 }

  function loadScenario(chosenPersona) {
    setScenarioLoading(true)
    setScenarioError(null)
    // A new scenario means a new session — clear everything from the last one.
    setExaminedClues(new Set())
    setSelectedClueId(null)
    setHistory([])
    setTurnsRemaining(TURN_LIMIT)
    setGkBusy(false)
    setGkError(null)
    setOutcome(null)
    setTalking(false)
    setBriefingOpen(true) // show the briefing again for the new scenario
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
  // NOTE: `properties` is carried here too, but is NOT rendered by the panel
  // (see ClueDetailPanel). It is the machine-readable evidence channel, used
  // to build object_properties for the Gatekeeper payload below.
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
        properties: clue.properties ?? {},
      }
    })
    return map
  }, [scenario])

  function handleExamine(clueId) {
    if (!clueId) return // empty markers carry no clue — nothing to examine
    setSelectedClueId(clueId)
    setExaminedClues((prev) => new Set(prev).add(clueId))
  }

  // ── The turn loop ────────────────────────────────────────────
  // Assemble the full game state, call the Gatekeeper, append both sides of
  // the exchange to history, decrement the counter, and read the decision.
  function handleSendTurn(playerText) {
    const text = playerText.trim()
    if (!text || gkBusy || outcome) return

    const examinedIds = [...examinedClues]

    // Build object_properties from every clue the player has examined — the
    // machine-readable evidence the Python check reasons over. Kept out of
    // the detail panel; surfaced only to the Gatekeeper.
    const objectProperties = {}
    examinedIds.forEach((cid) => {
      const clue = clueDetails[cid]
      if (clue) objectProperties[cid] = clue.properties ?? {}
    })

    // This player message becomes turn (TURN_LIMIT - turnsRemaining + 1).
    const turnNumber = TURN_LIMIT - turnsRemaining + 1
    const isFinalTurn = turnsRemaining <= 1

    // Optimistically show the player's line straight away.
    const historyWithPlayer = [...history, { role: 'player', text }]
    setHistory(historyWithPlayer)
    setGkBusy(true)
    setGkError(null)

    const gameState = {
      persona,
      scenario,
      session_id: scenario?.session_id ?? '',
      turn: turnNumber,
      turns_remaining: turnsRemaining,
      final_turn: isFinalTurn,
      player_inventory: examinedIds,
      examined_objects: examinedIds,
      object_properties: objectProperties,
      // Send history WITHOUT this turn's player line appended again — the
      // backend adds "PLAYER JUST SAID" separately, so passing it in both
      // places would duplicate it in the prompt.
      conversation_history: history,
      player_input: text,
    }

    sendTurn(gameState)
      .then((res) => {
        setHistory((prev) => [
          ...prev,
          { role: 'gatekeeper', text: res.response },
        ])
        setTurnsRemaining((prev) => Math.max(0, prev - 1))

        if (res.decision_type === 'GRANT_EXIT') {
          setOutcome('ESCAPE')
        } else if (res.decision_type === 'DENY_FINAL') {
          setOutcome('LOCKED')
        } else if (isFinalTurn) {
          // Safety net: the backend forces DENY_FINAL on the final turn, but
          // if anything slipped through, the turn limit still ends the game.
          setOutcome('LOCKED')
        }
      })
      .catch((err) => {
        // Roll the player's line back out of history so they can retry
        // cleanly rather than the message sitting there unanswered.
        setHistory((prev) => prev.slice(0, -1))
        setGkError(
          err instanceof GatekeeperClientError
            ? err.message
            : 'The Gatekeeper did not respond. Try again.'
        )
      })
      .finally(() => setGkBusy(false))
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
        <span className="titlebar-status">
          {outcome === 'ESCAPE'
            ? 'DOOR · OPEN'
            : outcome === 'LOCKED'
            ? 'SECURE ROOM · LOCKED'
            : 'SECURE ROOM · LOCKED'}
        </span>
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
              // Empty marker: render nothing and no interactive element at all.
              if (!clueId) return null

              const clue = clueDetails[clueId]
              const art = clue ? getClueArt(clue.art_key, m.surface) : null
              const examined = examinedClues.has(clueId)

              return (
                <button
                  key={m.id}
                  className={`clue-marker${examined ? ' clue-marker-examined' : ''}`}
                  style={{ left: `${m.x}%`, top: `${m.y}%` }}
                  data-zone={m.zone}
                  data-surface={m.surface}
                  onClick={() => handleExamine(clueId)}
                  aria-label={clue ? `Examine ${clue.name}` : 'Examine object'}
                >
                  {art?.found ? (
                    <img
                      className="clue-sprite"
                      src={art.src}
                      alt={clue.name}
                      style={art.style}
                    />
                  ) : (
                    // Fallback only when a placed clue's sprite fails to
                    // resolve — never for empty markers.
                    <span className="clue-sprite-missing" />
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
        <span>
          Turns remaining: <strong>{turnsRemaining}</strong>
        </span>
        <button
          className="statusbar-briefing"
          onClick={() => setBriefingOpen(true)}
        >
          Briefing
        </button>
        <span className="statusbar-hint">
          {outcome === 'ESCAPE'
            ? 'The door is open. You are free.'
            : outcome === 'LOCKED'
            ? 'You are locked in.'
            : talking
            ? 'Make your case.'
            : 'Click the Gatekeeper to speak.'}
        </span>
      </footer>

      <ClueDetailPanel clue={selectedClue} onClose={() => setSelectedClueId(null)} />

      {talking && (
        <GatekeeperDialogue
          persona={persona}
          history={history}
          busy={gkBusy}
          error={gkError}
          outcome={outcome}
          turnsRemaining={turnsRemaining}
          onSend={handleSendTurn}
          onClose={() => setTalking(false)}
        />
      )}

      {/* Rendered through a portal onto <body> so `position: fixed` pins to the
          viewport, not to any transformed ancestor inside .app. */}
      {briefingOpen &&
        createPortal(
          <div
            className="briefing-backdrop"
            role="dialog"
            aria-modal="true"
            aria-label="Mission briefing"
          >
            <div className="briefing-panel">
              <button
                className="briefing-close"
                onClick={() => setBriefingOpen(false)}
                aria-label="Close briefing"
              >
                ×
              </button>

              <p className="briefing-eyebrow">YOUR BRIEFING</p>
              <h2 className="briefing-role">
                You are being questioned by{' '}
                {scenario.gatekeeper_role ?? 'the Gatekeeper'}
              </h2>

              {scenario.player_backstory && (
                <div className="briefing-block">
                  <span className="briefing-label">Your cover story</span>
                  <p className="briefing-text">{scenario.player_backstory}</p>
                </div>
              )}

              {scenario.suspicion_context && (
                <div className="briefing-block">
                  <span className="briefing-label">Why you're under suspicion</span>
                  <p className="briefing-text">{scenario.suspicion_context}</p>
                </div>
              )}

              <p className="briefing-hint">
                Search the room for evidence, then click the Gatekeeper to make
                your case.
              </p>

              <button
                className="briefing-begin"
                onClick={() => setBriefingOpen(false)}
              >
                Begin
              </button>
            </div>
          </div>,
          document.body
        )}
    </div>
  )
}

export default App