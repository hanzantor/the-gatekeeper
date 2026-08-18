// GatekeeperDialogue.jsx — the talk-to-the-Gatekeeper modal, opened by
// clicking GatekeeperCharacter. App.jsx owns the turn loop and the state;
// this component is the view + input surface for it.
//
// Props (all from App.jsx):
//   persona         'suspicious' | 'fair' | 'corruptible' — picks the opener
//   history         [{ role: 'player' | 'gatekeeper', text }]
//   busy            true while waiting on the model — disables input, shows
//                   the typing indicator
//   error           string | null — last turn's error (e.g. backend down)
//   outcome         null | 'ESCAPE' | 'LOCKED' — freezes input when the game
//                   has ended
//   turnsRemaining  number — shown so the player feels the clock
//   onSend(text)    hand a player message up to App.jsx's turn loop
//   onClose()       close the modal (the session keeps its state)
//
// Reuses ClueDetailPanel's `.clue-panel-backdrop` / `.clue-panel` chrome so
// both modals share one visual language.

import { useEffect, useRef, useState } from 'react'

// Per-persona session-opening line (spec §18). Shown before the player has
// said anything; once history exists, the real exchange takes over.
const OPENING_LINES = {
  suspicious:
    'Security protocol active. You have been found in a restricted area. State your business — clearly, and without embellishment.',
  fair: 'Access restricted. I will hear your case. Be honest and I will be reasonable.',
  corruptible:
    'Legacy protocol active. This unit has… some flexibility. Approach accordingly.',
}

function GatekeeperDialogue({
  persona,
  history = [],
  busy = false,
  error = null,
  outcome = null,
  turnsRemaining,
  onSend,
  onClose,
}) {
  const [draft, setDraft] = useState('')
  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  const ended = outcome === 'ESCAPE' || outcome === 'LOCKED'
  const opener = OPENING_LINES[persona] ?? OPENING_LINES.fair

  // Keep the transcript pinned to the newest line as it grows / while typing.
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [history, busy])

  // Focus the field whenever the Gatekeeper is ready for input.
  useEffect(() => {
    if (!busy && !ended) inputRef.current?.focus()
  }, [busy, ended])

  function submit() {
    const text = draft.trim()
    if (!text || busy || ended) return
    onSend(text)
    setDraft('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

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

          <div className="dialogue-transcript" ref={scrollRef}>
            {/* Opening line, shown until the real conversation begins. */}
            {history.length === 0 && (
              <p className="gatekeeper-line dialogue-msg dialogue-msg-gatekeeper">
                {opener}
              </p>
            )}

            {history.map((turn, i) => (
              <p
                key={i}
                className={`dialogue-msg ${
                  turn.role === 'player'
                    ? 'dialogue-msg-player'
                    : 'dialogue-msg-gatekeeper gatekeeper-line'
                }`}
              >
                {turn.role === 'player' ? (
                  <span className="dialogue-speaker">YOU</span>
                ) : (
                  <span className="dialogue-speaker">GATEKEEPER</span>
                )}
                {turn.text}
              </p>
            ))}

            {busy && (
              <p className="dialogue-msg dialogue-msg-gatekeeper dialogue-typing">
                <span className="dialogue-speaker">GATEKEEPER</span>
                <span className="dialogue-dots">
                  <span />
                  <span />
                  <span />
                </span>
              </p>
            )}
          </div>

          {/* Outcome banner — the door opened, or the room is sealed. */}
          {outcome === 'ESCAPE' && (
            <p className="dialogue-outcome dialogue-outcome-escape">
              THE DOOR OPENS. You are free.
            </p>
          )}
          {outcome === 'LOCKED' && (
            <p className="dialogue-outcome dialogue-outcome-locked">
              THE DOOR STAYS SHUT. You are locked in.
            </p>
          )}

          {error && <p className="dialogue-error">{error}</p>}

          {!ended && (
            <div className="terminal-input">
              <input
                ref={inputRef}
                type="text"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  busy ? 'The Gatekeeper is considering…' : 'Type your response…'
                }
                className="terminal-field"
                disabled={busy}
                aria-label="Your response to the Gatekeeper"
              />
              <button
                className="terminal-send"
                onClick={submit}
                disabled={busy || !draft.trim()}
              >
                SEND
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default GatekeeperDialogue