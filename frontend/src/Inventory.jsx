// Inventory.jsx — thumbnail strip of clues the player has examined this
// session (the_gatekeeper_spec.md §7: "Inventory panel: thumbnails of
// examined objects this session"). Clicking a thumbnail reopens that
// clue's detail panel — useful once the room has more than a couple of
// examined objects and the player wants to re-check something before
// answering the Gatekeeper.
//
// `details` is keyed the same way as ClueDetailPanel's data: art_key ->
// { name, description, properties }. Only `name` is used here, and it's
// optional — an examined clue with no name yet (not in the stub, or not
// yet returned by the scenario) just falls back to showing its art_key.

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
          examinedKeys.map((artKey) => {
            const art = getPanelArt(artKey, THUMB_SIZE)
            const label = details?.[artKey]?.name ?? artKey

            return (
              <button
                key={artKey}
                className="inventory-item"
                onClick={() => onSelect(artKey)}
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