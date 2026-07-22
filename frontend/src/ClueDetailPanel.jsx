// ClueDetailPanel.jsx — shown when the player clicks an examinable clue.
//
// Layout: object sprite in the top-left, name + one-line description + a
// bulleted list of concrete details on the right. The bullets are the
// load-bearing part — they're what the player actually reads and reasons
// from when deciding what to say to the Gatekeeper.
//
// NOTE: the clue's machine-readable `properties` are deliberately NOT shown.
// Those flags exist for the Python evidence checker and the Gatekeeper's
// cross-reference; rendering them to the player leaked the clue's role
// ("Neutral") and produced inverted-negative artefacts ("Not Not Standard").
// `detail_points` is the player-facing channel; `properties` is the machine one.
//
// `clue` shape (matches the live /api/scenario response, spec §5):
//   {
//     art_key: 'work_order',
//     name: 'Access Authorization',
//     description: 'A work order granting access to restricted areas.',
//     detail_points: [
//       'Work Order #73456, issued 12 April',
//       'Signed by the Head of Security',
//       'Covers equipment calibration in Section C-8',
//       'Valid until 1 May',
//     ],
//   }

import { getPanelArt } from './data/clueArtMap.js'

function ClueDetailPanel({ clue, onClose }) {
  if (!clue) return null

  const art = getPanelArt(clue.art_key)
  const points = clue.detail_points ?? []

  return (
    <div className="clue-panel-backdrop" onClick={onClose}>
      <div
        className="clue-panel"
        role="dialog"
        aria-label={clue.name}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="clue-panel-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        <div className="clue-panel-image">
          {art.found ? (
            <img src={art.src} alt={clue.name} style={art.style} />
          ) : (
            <span className="clue-panel-image-missing" />
          )}
        </div>

        <div className="clue-panel-content">
          <h3 className="clue-panel-name">{clue.name}</h3>

          {clue.description && (
            <p className="clue-panel-description">{clue.description}</p>
          )}

          {points.length > 0 && (
            <ul className="clue-panel-bullets">
              {points.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

export default ClueDetailPanel