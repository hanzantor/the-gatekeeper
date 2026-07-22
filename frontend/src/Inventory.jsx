// Inventory.jsx — thumbnail strip of clues the player has examined this
// session (the_gatekeeper_spec.md §7: "Inventory panel: thumbnails of
// examined objects this session"). Clicking a thumbnail reopens that
// clue's detail panel.
//
// KEYING NOTE: entries are keyed by clue `id`, not `art_key` — several clues
// share a sprite, so art_key is not unique within a scenario. The sprite is
// looked up via the clue record's own art_key field instead.
//
// `details` is keyed the same way as ClueDetailPanel's data: clue id ->
// { id, art_key, name, description, detail_points }.

import { getPanelArt } from './data/clueArtMap.js'

const THUMB_SIZE = 40

function Inventory({ examinedKeys, details, onSelect }) {
  return (
    <section className="inventory">
      <div className="inventory-header">
        <span className="inventory-dot" />
        EXAMINED ({examinedKeys.length})
      </div>

      <div className="inventory-items">
        {examinedKeys.length === 0 ? (
          <p className="inventory-empty">Nothing examined yet.</p>
        ) : (
          examinedKeys.map((clueId) => {
            const clue = details?.[clueId]
            const art = getPanelArt(clue?.art_key, THUMB_SIZE)
            const label = clue?.name ?? clueId

            return (
              <button
                key={clueId}
                className="inventory-item"
                onClick={() => onSelect(clueId)}
                aria-label={`Reopen ${label}`}
                title={label}
              >
                <span className="inventory-item-thumb">
                  {art.found ? (
                    <img src={art.src} alt={label} style={art.style} />
                  ) : (
                    <span className="inventory-item-missing" />
                  )}
                </span>
                <span className="inventory-item-label">{label}</span>
              </button>
            )
          })
        )}
      </div>
    </section>
  )
}

export default Inventory