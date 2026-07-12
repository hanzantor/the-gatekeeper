/**
 * clueArtMap.js — The Gatekeeper
 *
 * Single-angle sprite model. Every clue has exactly ONE sprite file at
 *   frontend/public/clues/<art_key>.png
 * All 25 sprites are pre-cropped to content and padded to their own centered
 * square canvas (square_pad.py), so a plain <img> with width set and
 * height:auto always renders the object centered in its own box.
 *
 * IMPORTANT — centering is owned by the CALLER, not this file.
 * getClueArt() returns ONLY sizing, mirroring, and shadow. It does NOT
 * return position or a centering transform. The marker <button> in App.jsx
 * must center its contents itself (flexbox: align-items/justify-content:
 * center). If both this file AND the button try to center the image, the
 * two centering operations stack and the sprite drifts off the marker
 * point — that was the up-and-left offset bug.
 *
 * Two things vary per clue:
 *
 *   scale     Relative real-world size. Without this a business card and a
 *             wall clock render at the same pixel size and the room reads
 *             as a collage. This is the single biggest thing that sells it.
 *
 *   footprint How the object was drawn — 'flat' (lying down, seen from
 *             above: paper, cards, phones, tools) or 'upright' (standing:
 *             mug, clock, plant, box, jacket, folder). Only used to pick
 *             the right shadow shape.
 */

const BASE = '/clues';

/** Nominal sprite size in px before per-clue and per-surface scaling. */
const BASE_SIZE = 72;

/* ------------------------------------------------------------------ *
 * art_key -> sprite + relative size + how it was drawn
 * Keys must match the art_key values emitted in the scenario JSON.
 * ------------------------------------------------------------------ */
export const CLUE_META = {
  // --- supporting (6) -------------------------------------------------
  appointment_letter: { file: 'appointment_letter.png', scale: 0.85, footprint: 'flat' },
  access_log:         { file: 'access_log.png',         scale: 0.85, footprint: 'flat' },
  work_order:         { file: 'work_order.png',         scale: 0.90, footprint: 'flat' },
  email_printout:     { file: 'email_printout.png',     scale: 0.85, footprint: 'flat' },
  calendar_invite:    { file: 'calendar_invite.png',    scale: 0.55, footprint: 'flat' },
  delivery_docket:    { file: 'delivery_docket.png',    scale: 0.70, footprint: 'flat' },

  // --- identity (5) ---------------------------------------------------
  access_badge:       { file: 'access_badge.png',       scale: 0.60, footprint: 'flat' },
  staff_id:           { file: 'staff_id.png',           scale: 0.50, footprint: 'flat' },
  lanyard:            { file: 'lanyard.png',            scale: 0.75, footprint: 'flat' },
  business_card:      { file: 'business_card.png',      scale: 0.45, footprint: 'flat' },
  phone_message:      { file: 'phone_message.png',      scale: 0.60, footprint: 'flat' },

  // --- neutral (8) ----------------------------------------------------
  coffee_mug:         { file: 'coffee_mug.png',         scale: 0.65, footprint: 'upright' },
  notebook:           { file: 'notebook.png',           scale: 0.85, footprint: 'flat' },
  jacket:             { file: 'jacket.png',             scale: 0.95, footprint: 'upright' },
  wall_clock:         { file: 'wall_clock.png',         scale: 0.70, footprint: 'upright' },
  framed_photo:       { file: 'framed_photo.png',       scale: 0.75, footprint: 'upright' },
  potted_plant:       { file: 'potted_plant.png',       scale: 0.85, footprint: 'upright' },
  food_wrapper:       { file: 'food_wrapper.png',       scale: 0.55, footprint: 'flat' },
  manual:             { file: 'manual.png',             scale: 0.80, footprint: 'flat' },

  // --- incriminating (6) ----------------------------------------------
  document_folder:    { file: 'document_folder.png',    scale: 0.90, footprint: 'flat' },
  storage_box:        { file: 'storage_box.png',        scale: 1.00, footprint: 'upright' },
  pry_bar:            { file: 'pry_bar.png',            scale: 1.00, footprint: 'flat' },
  burner_phone:       { file: 'burner_phone.png',       scale: 0.55, footprint: 'flat' },
  gloves:             { file: 'gloves.png',             scale: 0.70, footprint: 'flat' },
  torch:              { file: 'torch.png',              scale: 0.60, footprint: 'flat' },
};

/* ------------------------------------------------------------------ *
 * Shadows. Flat objects hug the surface; upright objects cast lower and
 * softer so they read as standing on it rather than hovering.
 * ------------------------------------------------------------------ */
const SHADOW = {
  shelf: {
    flat:    'drop-shadow(1px 2px 0 rgba(0,0,0,0.28))',
    upright: 'drop-shadow(2px 3px 1px rgba(0,0,0,0.32))',
  },
  desk: {
    flat:    'drop-shadow(2px 3px 0 rgba(0,0,0,0.34))',
    upright: 'drop-shadow(3px 4px 1px rgba(0,0,0,0.38))',
  },
  floor: {
    flat:    'drop-shadow(2px 4px 1px rgba(0,0,0,0.42))',
    upright: 'drop-shadow(3px 6px 2px rgba(0,0,0,0.46))',
  },
};

/* ------------------------------------------------------------------ *
 * Surfaces. The ONLY transform this file ever applies is the mirror for
 * shelf_right — never a centering translate. Centering is the marker
 * button's job (flexbox), so this transform can be safely appended to
 * without fighting anything else.
 * ------------------------------------------------------------------ */
export const SURFACE_STYLES = {
  shelf_left:  { mirror: false, scale: 1.00, shadow: 'shelf' },
  shelf_right: { mirror: true,  scale: 1.00, shadow: 'shelf' }, // mirrored, never generated
  desk:        { mirror: false, scale: 0.88, shadow: 'desk'  },
  floor:       { mirror: false, scale: 0.78, shadow: 'floor' },
};

const DEFAULT_SURFACE = 'shelf_left';

/**
 * Resolve a clue's sprite and visual style for a marker surface.
 *
 * @param {string}  artKey   art_key from the scenario JSON
 * @param {string}  surface  shelf_left | shelf_right | desk | floor
 * @param {boolean} forceFlip  optional per-MARKER mirror override, independent
 *                             of surface. Some markers on shelf_left/desk/floor
 *                             read better mirrored purely for visual variety —
 *                             e.g. a run of shelf objects all facing the same
 *                             way looks copy-pasted. This flips the sprite
 *                             WITHOUT touching which shadow/scale applies,
 *                             because that's still owned by `surface`.
 *                             shelf_right always mirrors regardless of this
 *                             flag — forceFlip toggles ON TOP of the surface's
 *                             own mirror, so shelf_right + forceFlip=true
 *                             cancels out back to unmirrored. In practice you
 *                             will only ever set this for shelf_left/desk/
 *                             floor markers.
 * @returns {{ src: string|null, found: boolean, style: object }}
 *
 * The returned style controls ONLY size, mirroring, and shadow — never
 * position. The caller's marker button must center its own contents
 * (display:flex; align-items:center; justify-content:center). Do not add
 * `position` or a centering `translate` here — that reintroduces the
 * double-centering bug.
 *
 * found === false means there is no sprite for this art_key. Render the
 * pulsing marker dot instead of a broken image.
 */
export function getClueArt(artKey, surface = DEFAULT_SURFACE, forceFlip = false) {
  const meta = CLUE_META[artKey];
  const surf = SURFACE_STYLES[surface] ?? SURFACE_STYLES[DEFAULT_SURFACE];

  if (!meta) {
    return { src: null, found: false, style: {} };
  }

  const size = BASE_SIZE * meta.scale * surf.scale;
  const mirrored = surf.mirror !== forceFlip; // XOR: surface mirror vs marker override

  return {
    src: `${BASE}/${meta.file}`,
    found: true,
    style: {
      width: `${Math.round(size)}px`,
      height: 'auto',
      transform: mirrored ? 'scaleX(-1)' : 'none',
      filter: SHADOW[surf.shadow][meta.footprint], // unaffected by flip — shadow stays correct for the surface
      imageRendering: 'pixelated',
      display: 'block',
    },
  };
}

/** True if a sprite exists for this art_key. */
export function hasClueArt(artKey) {
  return Object.prototype.hasOwnProperty.call(CLUE_META, artKey);
}

/** Fixed display size for the clue detail panel, in px. */
const PANEL_SIZE = 128;

/**
 * Resolve a clue's sprite for the detail panel — the large view shown when
 * a player clicks a marker. Deliberately ignores surface (no shelf/desk/
 * floor scaling) and shadow: those exist to sell placement *in the room*,
 * not in a flat UI panel. Every clue renders at the same panel size so the
 * panel layout never has to reflow around image size.
 *
 * @param {string} artKey
 * @returns {{ src: string|null, found: boolean, style: object }}
 */
export function getPanelArt(artKey) {
  const meta = CLUE_META[artKey];
  if (!meta) {
    return { src: null, found: false, style: {} };
  }
  return {
    src: `${BASE}/${meta.file}`,
    found: true,
    style: {
      width: `${PANEL_SIZE}px`,
      height: 'auto',
      imageRendering: 'pixelated',
      display: 'block',
    },
  };
}

/** Every art_key with art — handy for asserting the clue library matches. */
export const ART_KEYS = Object.keys(CLUE_META);