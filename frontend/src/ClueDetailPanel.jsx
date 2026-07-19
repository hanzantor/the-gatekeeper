// ClueDetailPanel.jsx — shown when the player clicks an examinable clue.
//
// Layout: object sprite in the top-left, name + description + story detail +
// a bulleted list of properties on the right. The `detail` paragraph is the
// narrative texture (who a phone called, who signed a letter) that makes each
// clue feel like it belongs to a real situation; the bullets are the terse,
// machine-readable properties the player reasons from.
//
// `clue` shape (matches the live /api/scenario response, spec §5):
//   {
//     art_key: 'burner_phone',
//     name: 'Disposable Smartphone',
//     description: 'A cheap prepaid phone.',
//     detail: 'Its call log shows three calls to a "D. Evans" between
//              01:40 and 02:05 last night, all under a minute.',
//     properties: ['Calls to D. Evans', 'Last used 02:05', 'No contacts saved'],
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

          {clue.detail && (
            <p className="clue-panel-detail">{clue.detail}</p>
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