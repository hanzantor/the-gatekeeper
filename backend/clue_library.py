# clue_library.py — clue catalogue + the picker that builds a balanced set per scenario.

import random

CLUE_LIBRARY = [
    # supporting
    {"id": "appointment_letter",  "art_key": "appointment_letter", "role": "supporting",   "name": "Appointment Letter",      "room": "shared"},
    {"id": "access_log",          "art_key": "access_log",         "role": "supporting",   "name": "Access Log Terminal",     "room": "shared"},
    {"id": "work_order",          "art_key": "work_order",         "role": "supporting",   "name": "Work Order",              "room": "shared"},
    {"id": "signed_authorisation","art_key": "delivery_docket",    "role": "supporting",   "name": "Signed Authorisation",   "room": "shared"},
    {"id": "asset_tag_equipment", "art_key": "manual",             "role": "supporting",   "name": "Asset-Tagged Equipment", "room": "shared"},
    {"id": "email_printout",      "art_key": "email_printout",     "role": "supporting",   "name": "Email Printout",         "room": "shared"},

    # identity
    {"id": "staff_id",            "art_key": "staff_id",           "role": "identity",     "name": "Staff ID Card",          "room": "shared"},
    {"id": "visitor_badge",       "art_key": "access_badge",       "role": "identity",     "name": "Visitor Badge",          "room": "shared"},
    {"id": "lanyard",             "art_key": "lanyard",            "role": "identity",     "name": "Lanyard",                "room": "shared"},
    {"id": "business_card",       "art_key": "business_card",      "role": "identity",     "name": "Business Card",          "room": "shared"},

    # neutral
    {"id": "coffee_mugs",         "art_key": "coffee_mug",         "role": "neutral",      "name": "Two Coffee Mugs",        "room": "shared"},
    {"id": "notebook",            "art_key": "notebook",           "role": "neutral",      "name": "Half-Finished Notebook", "room": "shared"},
    {"id": "jacket",              "art_key": "jacket",             "role": "neutral",      "name": "Jacket on a Chair",      "room": "shared"},
    {"id": "wall_clock",          "art_key": "wall_clock",         "role": "neutral",      "name": "Wall Clock",             "room": "shared"},
    {"id": "food_wrapper",        "art_key": "food_wrapper",       "role": "neutral",      "name": "Food Wrapper",           "room": "shared"},
    {"id": "framed_photo",        "art_key": "framed_photo",       "role": "neutral",      "name": "Framed Photo",           "room": "shared"},
    {"id": "potted_plant",        "art_key": "potted_plant",       "role": "neutral",      "name": "Potted Plant",           "room": "shared"},

    # incriminating
    {"id": "pry_bar",             "art_key": "pry_bar",            "role": "incriminating", "name": "Pry Bar",               "room": "shared"},
    {"id": "wrong_keycard",       "art_key": "access_badge",       "role": "incriminating", "name": "Someone Else's Keycard","room": "shared"},
    {"id": "burner_phone",        "art_key": "burner_phone",       "role": "incriminating", "name": "Burner Phone",          "room": "shared"},
    {"id": "gloves",              "art_key": "gloves",             "role": "incriminating", "name": "Gloves",                "room": "shared"},
    {"id": "torch",               "art_key": "torch",              "role": "incriminating", "name": "Torch",                 "room": "shared"},
    {"id": "phone_message",       "art_key": "phone_message",      "role": "incriminating", "name": "Phone With a Message",  "room": "shared"},

    # room-specific signature clues
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
    # Quota: >=2 supporting, >=1 neutral, >=1 incriminating, 4-6 total.
    # No two clues in one scenario may share an art_key (avoids duplicate sprites in a room).
    available = [c for c in CLUE_LIBRARY if c["room"] in ("shared", room)]

    chosen = []
    used_art_keys = set()

    def pick(role, n):
        # Pick one at a time and mark the sprite used before the next draw.
        # Batch sampling could return two clues sharing a sprite before either was marked.
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

    # meet the minimum quota first
    chosen += pick("supporting", 2)
    chosen += pick("neutral", 1)
    chosen += pick("incriminating", 1)

    # fill up to a random total, still refusing any sprite already on the table
    target_total = random.randint(min_total, max_total)
    chosen_ids = {c["id"] for c in chosen}
    remaining_pool = [c for c in available if c["id"] not in chosen_ids]
    random.shuffle(remaining_pool)

    while len(chosen) < target_total and remaining_pool:
        candidate = remaining_pool.pop()
        # re-check against the current used set as it keeps growing
        if candidate["art_key"] in used_art_keys:
            continue
        chosen.append(candidate)
        used_art_keys.add(candidate["art_key"])

    random.shuffle(chosen)  # so role order isn't predictable in the room
    return chosen