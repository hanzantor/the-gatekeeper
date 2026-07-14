// GatekeeperCharacter.jsx — clickable placeholder standing next to the
// door. Currently a plain rectangle; swap the placeholder span for a real
// character sprite/animation later without changing how App.jsx uses this
// component (position props and onClick stay the same).
//
// Position (x, y) is passed in as room-relative percentages, same
// coordinate system as the clue markers, so it's placed the same way —
// but it isn't one of the 21 fixed clue markers (§ Marker & Clue Position
// System) since it's not a clue the Gatekeeper reasons about; it's the
// Gatekeeper itself.

function GatekeeperCharacter({ x, y, onClick }) {
  return (
    <button
      className="gatekeeper-character"
      style={{ left: `${x}%`, top: `${y}%` }}
      onClick={onClick}
      aria-label="Talk to the Gatekeeper"
    >
      <span className="gatekeeper-character-placeholder" />
    </button>
  )
}

export default GatekeeperCharacter