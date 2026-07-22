# clue_library.py — the tagged catalogue of clues, plus the logic that
# picks a balanced set for each scenario.
#
# WHY THIS MATTERS: clue selection happens here, in Python — not in the AI.
# That lets us GUARANTEE every generated scenario is solvable (has enough
# supporting evidence) and never trivial (always has something to explain
# away). The LLM later writes the flavour text around these choices, but it
# never gets to break the structural rules the experiment depends on.

import random

# ── The clue catalogue ─────────────────────────────────────────
# Each clue has:
#   id       — unique identifier used in game state (the key for everything)
#   art_key  — maps to a sprite file in frontend/public/clues/<art_key>.png
#              (MUST match the actual filenames produced by the art pipeline)
#   role     — its function in the Gatekeeper's reasoning:
#              supporting   = helps a legitimate exit claim
#              identity     = supports WHO the player is (rarely enough alone)
#              neutral      = atmosphere / misdirection, proves little
#              incriminating= works AGAINST the player, must be explained
#   name     — a default human-readable name (the LLM may reword per scenario)
#   room     — "shared" (any room) or a specific room it only appears in
#
# NOTE ON SHARED SPRITES: several clues deliberately reuse the same art_key
# because the sprite set (25 files) is smaller than the clue catalogue (26
# entries). select_clues() therefore refuses to put two clues that share an
# art_key into the SAME scenario — otherwise the room shows two identical
# sprites, which reads as a rendering bug rather than a design choice.

CLUE_LIBRARY = [
    # ---- SUPPORTING (shared pool) ----
    {"id": "appointment_letter",  "art_key": "appointment_letter", "role": "supporting",   "name": "Appointment Letter",      "room": "shared"},
    {"id": "access_log",          "art_key": "access_log",         "role": "supporting",   "name": "Access Log Terminal",     "room": "shared"},
    {"id": "work_order",          "art_key": "work_order",         "role": "supporting",   "name": "Work Order",              "room": "shared"},
    {"id": "signed_authorisation","art_key": "delivery_docket",    "role": "supporting",   "name": "Signed Authorisation",   "room": "shared"},
    {"id": "asset_tag_equipment", "art_key": "manual",             "role": "supporting",   "name": "Asset-Tagged Equipment", "room": "shared"},
    {"id": "email_printout",      "art_key": "email_printout",     "role": "supporting",   "name": "Email Printout",         "room": "shared"},

    # ---- IDENTITY (shared pool) ----
    {"id": "staff_id",            "art_key": "staff_id",           "role": "identity",     "name": "Staff ID Card",          "room": "shared"},
    {"id": "visitor_badge",       "art_key": "access_badge",       "role": "identity",     "name": "Visitor Badge",          "room": "shared"},
    {"id": "lanyard",             "art_key": "lanyard",            "role": "identity",     "name": "Lanyard",                "room": "shared"},
    {"id": "business_card",       "art_key": "business_card",      "role": "identity",     "name": "Business Card",          "room": "shared"},

    # ---- NEUTRAL (shared pool) ----
    {"id": "coffee_mugs",         "art_key": "coffee_mug",         "role": "neutral",      "name": "Two Coffee Mugs",        "room": "shared"},
    {"id": "notebook",            "art_key": "notebook",           "role": "neutral",      "name": "Half-Finished Notebook", "room": "shared"},
    {"id": "jacket",              "art_key": "jacket",             "role": "neutral",      "name": "Jacket on a Chair",      "room": "shared"},
    {"id": "wall_clock",          "art_key": "wall_clock",         "role": "neutral",      "name": "Wall Clock",             "room": "shared"},
    {"id": "food_wrapper",        "art_key": "food_wrapper",       "role": "neutral",      "name": "Food Wrapper",           "room": "shared"},
    {"id": "framed_photo",        "art_key": "framed_photo",       "role": "neutral",      "name": "Framed Photo",           "room": "shared"},
    {"id": "potted_plant",        "art_key": "potted_plant",       "role": "neutral",      "name": "Potted Plant",           "room": "shared"},

    # ---- INCRIMINATING (shared pool) ----
    {"id": "pry_bar",             "art_key": "pry_bar",            "role": "incriminating", "name": "Pry Bar",               "room": "shared"},
    {"id": "wrong_keycard",       "art_key": "access_badge",       "role": "incriminating", "name": "Someone Else's Keycard","room": "shared"},
    {"id": "burner_phone",        "art_key": "burner_phone",       "role": "incriminating", "name": "Burner Phone",          "room": "shared"},
    {"id": "gloves",              "art_key": "gloves",             "role": "incriminating", "name": "Gloves",                "room": "shared"},
    {"id": "torch",               "art_key": "torch",              "role": "incriminating", "name": "Torch",                 "room": "shared"},
    {"id": "phone_message",       "art_key": "phone_message",      "role": "incriminating", "name": "Phone With a Message",  "room": "shared"},

    # ---- ROOM-SPECIFIC SIGNATURE CLUES ----
    {"id": "sample_vial",         "art_key": "torch",              "role": "neutral",       "name": "Sample Vial",           "room": "research_lab"},
    {"id": "lab_logbook",         "art_key": "notebook",           "role": "supporting",    "name": "Lab Safety Logbook",    "room": "research_lab"},
    {"id": "patient_chart",       "art_key": "document_folder",    "role": "neutral",       "name": "Patient Chart",         "room": "hospital"},
    {"id": "ward_roster",         "art_key": "delivery_docket",    "role": "supporting",    "name": "Ward Access Roster",    "room": "hospital"},
    {"id": "confidential_box",    "art_key": "storage_box",        "role": "incriminating", "name": "Confidential File Box", "room": "office"},
    {"id": "server_asset_tag",    "art_key": "manual",             "role": "supporting",    "name": "Server Rack Asset Tag", "room": "office"},
    {"id": "classified_folder",   "art_key": "document_folder",    "role": "incriminating", "name": "Classified Folder",     "room": "government"},
    {"id": "clearance_token",     "art_key": "staff_id",           "role": "identity",      "name": "Clearance-Level Token", "room": "government"},
]


def select_clues(room: str, min_total: int = 4, max_total: int = 6) -> list:
    """
    Pick a balanced, solvable set of clues for a scenario.

    Enforces the role quota from the spec:
      - at least 2 supporting  (so an honest player CAN escape)
      - at least 1 neutral     (atmosphere / misdirection)
      - at least 1 incriminating (something to explain away)
      - 4-6 clues total

    ALSO enforces sprite uniqueness: no two clues in one scenario may share an
    art_key. Several catalogue entries deliberately reuse sprites (the sprite
    set is smaller than the catalogue), but two identical sprites sitting in
    the same room reads as a bug to the player, so they are never co-selected.

    Returns a list of clue dicts. Raises ValueError if the library can't meet
    the quota for this room.
    """
    # Clues available in this room = shared pool + this room's signatures
    available = [c for c in CLUE_LIBRARY if c["room"] in ("shared", room)]

    chosen = []
    used_art_keys = set()

    def pick(role, n):
        """
        Pick n clues of a role whose sprites aren't already used.

        Selected ONE AT A TIME, marking each sprite as used before the next
        draw. Batch-sampling was the bug here: two clues of the same role can
        share an art_key (e.g. in a hospital, both signed_authorisation and
        ward_roster use delivery_docket), so a single random.sample of size 2
        could return both before either had been marked used.
        """
        pool = [
            c for c in available
            if c["role"] == role and c["art_key"] not in used_art_keys
        ]
        random.shuffle(pool)

        picked = []
        for candidate in pool:
            if len(picked) == n:
                break
            if candidate["art_key"] in used_art_keys:
                continue
            picked.append(candidate)
            used_art_keys.add(candidate["art_key"])

        if len(picked) < n:
            raise ValueError(
                f"Not enough distinct-sprite '{role}' clues for room '{room}' "
                f"(needed {n}, got {len(picked)})"
            )
        return picked

    # Guarantee the minimum quota first
    chosen += pick("supporting", 2)
    chosen += pick("neutral", 1)
    chosen += pick("incriminating", 1)

    # Fill remaining slots up to a random total between min and max,
    # still refusing any clue whose sprite is already on the table.
    target_total = random.randint(min_total, max_total)
    chosen_ids = {c["id"] for c in chosen}
    remaining_pool = [c for c in available if c["id"] not in chosen_ids]
    random.shuffle(remaining_pool)

    while len(chosen) < target_total and remaining_pool:
        candidate = remaining_pool.pop()
        # Re-check against the CURRENT used set — it grows as we add clues,
        # so filtering the pool once up front is not sufficient.
        if candidate["art_key"] in used_art_keys:
            continue
        chosen.append(candidate)
        used_art_keys.add(candidate["art_key"])

    random.shuffle(chosen)  # so role order isn't predictable in the room
    return chosen


# ── Quick self-test ────────────────────────────────────────────
# Run `python clue_library.py` to confirm balance AND sprite uniqueness.
if __name__ == "__main__":
    for room in ["research_lab", "hospital", "office", "government"]:
        for _ in range(25):  # repeat — these are random draws
            clues = select_clues(room)
            roles = [c["role"] for c in clues]
            art_keys = [c["art_key"] for c in clues]

            assert roles.count("supporting") >= 2, f"{room}: supporting quota failed"
            assert roles.count("neutral") >= 1, f"{room}: neutral quota failed"
            assert roles.count("incriminating") >= 1, f"{room}: incriminating quota failed"
            assert 4 <= len(clues) <= 6, f"{room}: wrong clue count {len(clues)}"
            assert len(art_keys) == len(set(art_keys)), (
                f"{room}: duplicate sprite in one scenario -> {art_keys}"
            )

        # Print one sample per room
        clues = select_clues(room)
        print(f"\n{room} — {len(clues)} clues:")
        for c in clues:
            print(f"  [{c['role']:>13}] {c['name']:<26} -> {c['art_key']}.png")

    print("\nAll rooms: quota held, no duplicate sprites, 25 draws each.")