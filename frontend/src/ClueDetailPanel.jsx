// ClueDetailPanel.jsx — shown when the player clicks an examinable clue.
//
// Layout: object sprite in the top-left, name + description + a bulleted
// list of properties on the right. The bullets are the load-bearing part —
// they're what the player actually reads and reasons from when deciding
// what to say to the Gatekeeper.
//
// `clue` shape (matches what the real /api/scenario response will send,
// per the_gatekeeper_spec.md §5 — this component needs no changes when the
// test stub is swapped for live scenario data):
//   {
//     art_key: 'storage_box',
//     name: 'Storage Box',
//     description: 'A plain closed box with a fitted lid.',
//     properties: ['Sealed shut', 'No visible label', 'Sits on the shelf'],
//   }

import { getPanelArt } from './data/clueArtMap.js'

function ClueDetailPanel({ clue, onClose }) {
  if (!clue) return null

  const art = getPanelArt(clue.art_key)

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

          {clue.properties?.length > 0 && (
            <ul className="clue-panel-bullets">
              {clue.properties.map((point, i) => (
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