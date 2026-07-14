// GatekeeperDialogue.jsx — the talk-to-the-Gatekeeper modal, opened by
// clicking GatekeeperCharacter. Deliberately reuses ClueDetailPanel's
// `.clue-panel-backdrop` / `.clue-panel` classes rather than defining its
// own card chrome, so both modals share one visual language instead of
// drifting into two different "popup" styles.

function GatekeeperDialogue({ onClose }) {
  return (
    <div className="clue-panel-backdrop" onClick={onClose}>
      <div
        className="clue-panel dialogue-panel"
        role="dialog"
        aria-label="Gatekeeper"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="clue-panel-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        <div className="dialogue-content">
          <h3 className="clue-panel-name">GATEKEEPER</h3>

          <p className="gatekeeper-line">
            State your business. The door does not open for those who cannot explain themselves.
          </p>

          <div className="terminal-input">
            <input type="text" placeholder="Type your response…" className="terminal-field" />
            <button className="terminal-send">SEND</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GatekeeperDialogue