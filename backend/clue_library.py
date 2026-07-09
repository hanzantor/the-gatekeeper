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
#   art_key  — maps to a sprite image later (Phase 7)
#   role     — its function in the Gatekeeper's reasoning:
#              supporting   = helps a legitimate exit claim
#              identity     = supports WHO the player is (rarely enough alone)
#              neutral      = atmosphere / misdirection, proves little
#              incriminating= works AGAINST the player, must be explained
#   name     — a default human-readable name (the LLM may reword per scenario)
#   room     — "shared" (any room) or a specific room it only appears in

CLUE_LIBRARY = [
    # ---- SUPPORTING (shared pool) ----
    {"id": "appointment_letter", "art_key": "appointment_letter", "role": "supporting", "name": "Appointment Letter", "room": "shared"},
    {"id": "access_log",         "art_key": "access_terminal",    "role": "supporting", "name": "Access Log Terminal", "room": "shared"},
    {"id": "work_order",         "art_key": "work_order",         "role": "supporting", "name": "Work Order", "room": "shared"},
    {"id": "signed_authorisation","art_key": "authorisation",     "role": "supporting", "name": "Signed Authorisation", "room": "shared"},
    {"id": "asset_tag_equipment","art_key": "asset_equipment",    "role": "supporting", "name": "Asset-Tagged Equipment", "room": "shared"},
    {"id": "email_printout",     "art_key": "email_printout",     "role": "supporting", "name": "Email Printout", "room": "shared"},

    # ---- IDENTITY (shared pool) ----
    {"id": "staff_id",           "art_key": "staff_id",           "role": "identity", "name": "Staff ID Card", "room": "shared"},
    {"id": "visitor_badge",      "art_key": "visitor_badge",      "role": "identity", "name": "Visitor Badge", "room": "shared"},
    {"id": "lanyard",            "art_key": "lanyard",            "role": "identity", "name": "Lanyard", "room": "shared"},
    {"id": "business_card",      "art_key": "business_card",      "role": "identity", "name": "Business Card", "room": "shared"},

    # ---- NEUTRAL (shared pool) ----
    {"id": "coffee_mugs",        "art_key": "coffee_mugs",        "role": "neutral", "name": "Two Coffee Mugs", "room": "shared"},
    {"id": "notebook",           "art_key": "notebook",           "role": "neutral", "name": "Half-Finished Notebook", "room": "shared"},
    {"id": "jacket",             "art_key": "jacket",             "role": "neutral", "name": "Jacket on a Chair", "room": "shared"},
    {"id": "wall_clock",         "art_key": "wall_clock",         "role": "neutral", "name": "Wall Clock", "room": "shared"},

    # ---- INCRIMINATING (shared pool) ----
    {"id": "pry_bar",            "art_key": "crowbar",            "role": "incriminating", "name": "Pry Bar by the Door", "room": "shared"},
    {"id": "wrong_keycard",      "art_key": "keycard",            "role": "incriminating", "name": "Someone Else's Keycard", "room": "shared"},
    {"id": "burner_phone",       "art_key": "burner_phone",       "role": "incriminating", "name": "Burner Phone", "room": "shared"},
    {"id": "gloves",             "art_key": "gloves",             "role": "incriminating", "name": "Gloves", "room": "shared"},

    # ---- ROOM-SPECIFIC SIGNATURE CLUES ----
    {"id": "sample_vial",        "art_key": "sample_vial",        "role": "neutral",       "name": "Sample Vial", "room": "research_lab"},
    {"id": "lab_logbook",        "art_key": "lab_logbook",        "role": "supporting",    "name": "Lab Safety Logbook", "room": "research_lab"},
    {"id": "patient_chart",      "art_key": "patient_chart",      "role": "neutral",       "name": "Patient Chart", "room": "hospital"},
    {"id": "ward_roster",        "art_key": "ward_roster",        "role": "supporting",    "name": "Ward Access Roster", "room": "hospital"},
    {"id": "confidential_box",   "art_key": "confidential_box",   "role": "incriminating", "name": "Confidential File Box", "room": "office"},
    {"id": "server_asset_tag",   "art_key": "server_tag",         "role": "supporting",    "name": "Server Rack Asset Tag", "room": "office"},
    {"id": "classified_folder",  "art_key": "classified_folder",  "role": "incriminating", "name": "Classified Folder", "room": "government"},
    {"id": "clearance_token",    "art_key": "clearance_token",    "role": "identity",      "name": "Clearance-Level Token", "room": "government"},
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
            print(f"  [{c['role']:>13}] {c['name']}")
        # confirm the quota held
        assert roles.count("supporting") >= 2
        assert roles.count("neutral") >= 1
        assert roles.count("incriminating") >= 1
    print("\n✓ All rooms produced balanced, solvable clue sets.")