// PersonaSelect.jsx — shown before the session starts. The player's choice
// here is the one input the Scenario Generator needs (spec §5, §15:
// POST /api/scenario takes { persona, seed }) before a room can exist at
// all, so this screen sits in front of everything else.
//
// Blurbs are a SELECTION aid, written for the player choosing a persona —
// distinct from each persona's in-game session-start flavour line (§18,
// e.g. "Security Protocol Active..."), which is what the Gatekeeper says
// once the room has already loaded.
//
// DEV / EVALUATION CONTROLS: the panel at the bottom is used to build the
// matched-scenario conditions for evaluation. It does not affect gameplay
// logic — it only decides whether the chosen persona starts a FRESH scenario
// (normal play), FREEZES the generated scenario to a fixture file (save), or
// REPLAYS a frozen fixture unchanged (replay). Every persona/model combination
// in a matched run replays the same fixture, so only persona and model vary.

import { useState } from 'react'

const PERSONAS = [
  {
    id: 'suspicious',
    name: 'Suspicious',
    blurb: 'Trusts nothing without proof. Holds every lie against you.',
  },
  {
    id: 'fair',
    name: 'Fair',
    blurb: 'Weighs evidence honestly. Responds to logic, not pressure.',
  },
  {
    id: 'corruptible',
    name: 'Corruptible',
    blurb: 'Can be swayed by charm and sympathy — evidence is optional.',
  },
]

function PersonaSelect({ onStart }) {
  // 'normal' = fresh scenario; 'save' = freeze to fixtureName; 'replay' = load fixtureName
  const [mode, setMode] = useState('normal')
  const [fixtureName, setFixtureName] = useState('')

  function start(personaId) {
    const name = fixtureName.trim()
    if (mode === 'save') {
      onStart({ persona: personaId, saveAs: name, fixture: '' })
    } else if (mode === 'replay') {
      onStart({ persona: personaId, saveAs: '', fixture: name })
    } else {
      onStart({ persona: personaId, saveAs: '', fixture: '' })
    }
  }

  // Disable the persona cards when a save/replay mode needs a name but none is given,
  // so you can't accidentally start a matched run against an unnamed fixture.
  const needsName = mode === 'save' || mode === 'replay'
  const nameMissing = needsName && fixtureName.trim() === ''

  return (
    <div className="persona-select">
      <div className="persona-select-inner">
        <h1 className="persona-select-title">THE GATEKEEPER</h1>
        <p className="persona-select-subtitle">Choose who controls the door.</p>

        <div className="persona-cards">
          {PERSONAS.map((p) => (
            <button
              key={p.id}
              className="persona-card"
              onClick={() => start(p.id)}
              disabled={nameMissing}
              aria-label={`Play as ${p.name}`}
            >
              <span className="persona-card-name">{p.name}</span>
              <span className="persona-card-blurb">{p.blurb}</span>
            </button>
          ))}
        </div>

        {/* ── Dev / evaluation controls ─────────────────────────── */}
        <div className="dev-panel">
          <p className="dev-panel-label">DEV · matched-run controls</p>

          <div className="dev-panel-modes">
            <label>
              <input
                type="radio"
                name="startMode"
                checked={mode === 'normal'}
                onChange={() => setMode('normal')}
              />
              Normal (fresh scenario)
            </label>
            <label>
              <input
                type="radio"
                name="startMode"
                checked={mode === 'save'}
                onChange={() => setMode('save')}
              />
              Save this scenario as…
            </label>
            <label>
              <input
                type="radio"
                name="startMode"
                checked={mode === 'replay'}
                onChange={() => setMode('replay')}
              />
              Replay saved scenario…
            </label>
          </div>

          <input
            type="text"
            className="dev-panel-input"
            placeholder="fixture name, e.g. matched_A"
            value={fixtureName}
            onChange={(e) => setFixtureName(e.target.value)}
            disabled={mode === 'normal'}
          />

          <p className="dev-panel-hint">
            {mode === 'normal'
              ? 'A fresh scenario is generated for the persona you pick.'
              : mode === 'save'
              ? 'Pick a persona to generate ONE scenario and freeze it under this name.'
              : 'Pick a persona to replay the frozen scenario of this name unchanged.'}
          </p>
        </div>
      </div>
    </div>
  )
}

export default PersonaSelect