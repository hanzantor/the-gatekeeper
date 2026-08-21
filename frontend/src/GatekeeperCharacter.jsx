// GatekeeperCharacter.jsx — clickable Gatekeeper standing next to the door.
// Renders a state sprite (idle / talking / grant / deny). Position (x, y) is
// room-relative %, same coordinate system as the clue markers, but it isn't
// one of the 21 clue markers — it's the Gatekeeper itself.

const SPRITES = {
  idle: '/gatekeeper/idle.png',
  talking: '/gatekeeper/thinking.png',
  grant: '/gatekeeper/granting.png',
  deny: '/gatekeeper/denying.png',
}

function GatekeeperCharacter({ x, y, state = 'idle', onClick }) {
  const src = SPRITES[state] ?? SPRITES.idle
  return (
    <button
      className="gatekeeper-character"
      style={{ left: `${x}%`, top: `${y}%` }}
      onClick={onClick}
      aria-label="Talk to the Gatekeeper"
    >
      <img className="gatekeeper-sprite" src={src} alt="The Gatekeeper" />
    </button>
  )
}

export default GatekeeperCharacter