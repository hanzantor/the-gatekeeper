// PersonaSelect.jsx — shown before the session starts. The player's choice
// here is the one input the Scenario Generator needs (spec §5, §15:
// POST /api/scenario takes { persona, seed }) before a room can exist at
// all, so this screen sits in front of everything else.
//
// Blurbs are a SELECTION aid, written for the player choosing a persona —
// distinct from each persona's in-game session-start flavour line (§18,
// e.g. "Security Protocol Active..."), which is what the Gatekeeper says
// once the room has already loaded.

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

function PersonaSelect({ onSelect }) {
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
              onClick={() => onSelect(p.id)}
              aria-label={`Play as ${p.name}`}
            >
              <span className="persona-card-name">{p.name}</span>
              <span className="persona-card-blurb">{p.blurb}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default PersonaSelect