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
#   id       — unique identifier used in game state
#   art_key  — maps to a sprite file in frontend/public/clues/<art_key>.png
#              (these MUST match the actual filenames produced by the art
#              pipeline — see the 25 sprites in public/clues/)
#   role     — its function in the Gatekeeper's reasoning:
#              supporting   = helps a legitimate exit claim
#              identity     = supports WHO the player is (rarely enough alone)
#              neutral      = atmosphere / misdirection, proves little
#              incriminating= works AGAINST the player, must be explained
#   name     — a default human-readable name (the LLM may reword per scenario)
#   room     — "shared" (any room) or a specific room it only appears in
#
# NOTE: a few art_key values are deliberate stand-ins where no dedicated
# sprite exists yet (e.g. sample_vial -> torch). They point at a REAL file
# so the clue always renders; refine them if/when more sprites are produced.

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

    # ---- INCRIMINATING (shared pool) ----
    {"id": "pry_bar",             "art_key": "pry_bar",            "role": "incriminating", "name": "Pry Bar by the Door",   "room": "shared"},
    {"id": "wrong_keycard",       "art_key": "access_badge",       "role": "incriminating", "name": "Someone Else's Keycard","room": "shared"},
    {"id": "burner_phone",        "art_key": "burner_phone",       "role": "incriminating", "name": "Burner Phone",          "room": "shared"},
    {"id": "gloves",              "art_key": "gloves",             "role": "incriminating", "name": "Gloves",                "room": "shared"},

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
    Clues are drawn from the shared pool plus this room's signature clues.

    Returns a list of clue dicts. Raises ValueError if the library can't
    meet the quota (a safety check — shouldn't happen with the catalogue above).
    """
    # Clues available in this room = shared pool + this room's signatures
    available = [c for c in CLUE_LIBRARY if c["room"] in ("shared", room)]

    def pick(role, n):
        pool = [c for c in available if c["role"] == role]
        if len(pool) < n:
            raise ValueError(f"Not enough '{role}' clues for room '{room}'")
        return random.sample(pool, n)

    # Guarantee the minimum quota first
    chosen = []
    chosen += pick("supporting", 2)
    chosen += pick("neutral", 1)
    chosen += pick("incriminating", 1)

    # Fill remaining slots up to a random total between min and max
    target_total = random.randint(min_total, max_total)
    remaining_pool = [c for c in available if c not in chosen]
    extra_needed = target_total - len(chosen)
    if extra_needed > 0 and remaining_pool:
        chosen += random.sample(remaining_pool, min(extra_needed, len(remaining_pool)))

    random.shuffle(chosen)  # so role order isn't predictable in the room
    return chosen


# ── Quick self-test ────────────────────────────────────────────
# Run `python clue_library.py` to see a sample selection and confirm balance.
if __name__ == "__main__":
    for room in ["research_lab", "hospital", "office", "government"]:
        clues = select_clues(room)
        roles = [c["role"] for c in clues]
        print(f"\n{room} — {len(clues)} clues:")
        for c in clues:
            print(f"  [{c['role']:>13}] {c['name']:<24} -> {c['art_key']}.png")
        # confirm the quota held
        assert roles.count("supporting") >= 2
        assert roles.count("neutral") >= 1
        assert roles.count("incriminating") >= 1
    print("\n✓ All rooms produced balanced, solvable clue sets.")