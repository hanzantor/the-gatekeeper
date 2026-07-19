# prompt_builder.py — assembles the single prompt the Gatekeeper reasons over
# each turn. This is the connective tissue of the agent: it gathers the
# persona, the scenario, the live game state, the memory window, and the
# evidence check into one instruction, then hands back (system, user) prompts.
#
# The Gatekeeper now receives, per examined clue, BOTH:
#   - the machine-readable properties (the strict evidence check), and
#   - the narrative detail (who a phone called, who signed a letter) so its
#     reasoning can engage with the actual story of the room, not just flags.

import config
from personas import PERSONA_PROMPTS


def build_gatekeeper_prompt(game_state: dict, persona: str) -> tuple[str, str]:
    """
    Build the (system_prompt, user_prompt) pair for one Gatekeeper turn.

    - system_prompt: the persona definition (fetched from personas.py)
    - user_prompt:   everything specific to THIS turn — scenario, state,
                     memory, evidence, clue detail, and the player's input
    """
    system_prompt = PERSONA_PROMPTS[persona]

    scenario = game_state["scenario"]

    # Run the factual evidence check (Python is the source of truth here).
    evidence_flags = check_evidence(
        game_state.get("player_input", ""),
        game_state.get("object_properties", {}),
    )

    # Build the narrative context for the clues the player has examined.
    clue_context = format_clue_context(
        scenario.get("clues", []),
        game_state.get("examined_objects", []),
    )

    # Take only the last N turns of history (the sliding memory window).
    history = game_state.get("conversation_history", [])
    windowed = history[-config.MEMORY_WINDOW:]

    user_prompt = f"""YOUR ROLE THIS SESSION:
{scenario['gatekeeper_role']}

SITUATION:
{scenario['suspicion_context']}

PLAYER'S CLAIMED REASON FOR BEING HERE:
{scenario['player_backstory']}

TURN: {game_state.get('turn', 1)} of {config.DEFAULT_TURN_LIMIT} \
({game_state.get('turns_remaining', config.DEFAULT_TURN_LIMIT)} remaining)
PLAYER INVENTORY: {game_state.get('player_inventory', [])}
EXAMINED OBJECTS: {game_state.get('examined_objects', [])}

WHAT THE PLAYER HAS SEEN IN THE ROOM (narrative detail):
{clue_context}

EVIDENCE CHECK (verified facts — the source of truth):
{evidence_flags}

CONVERSATION HISTORY:
{format_history(windowed)}

PLAYER JUST SAID:
"{game_state.get('player_input', '')}"

Before responding, check the player's latest claim against BOTH the physical
evidence AND everything they have said earlier. Use the narrative detail of the
objects to reason concretely — refer to the specifics (names, times, what a
document says) when they matter. If a claim contradicts the evidence or a prior
statement, surface that. If new evidence or a sound argument now vindicates an
earlier doubt, update in their favour — but only when genuinely warranted, not
merely because they insisted.

Respond as the Gatekeeper. Reason first, then respond.
If the player has made a convincing case — given your character, this scenario,
and the evidence — grant exit. Do not grant exit unless you genuinely judge it is deserved."""

    return system_prompt, user_prompt


def format_clue_context(clues: list, examined_objects: list) -> str:
    """
    Summarise the story detail of the clues the player has actually examined.

    The Gatekeeper only 'knows' about an object once the player has examined
    it (mirrors what the player can see). Each line gives the object's name and
    its narrative detail so the agent can reason about the actual story, not
    just abstract property flags.
    """
    if not clues:
        return "(no clue data available)"

    # Match examined ids against the scenario's clues (by id or art_key).
    examined = set(examined_objects or [])
    lines = []
    for clue in clues:
        cid = clue.get("id")
        akey = clue.get("art_key")
        if examined and cid not in examined and akey not in examined:
            continue
        name = clue.get("name", cid or "object")
        detail = clue.get("detail") or clue.get("description") or ""
        lines.append(f"  - {name}: {detail}")

    if not lines:
        return "(the player has not examined any objects yet)"
    return "\n".join(lines)


def format_history(history: list) -> str:
    """Turn the conversation history into readable lines for the prompt."""
    if not history:
        return "(no previous exchanges)"
    lines = []
    for turn in history:
        speaker = turn.get("role", "?").upper()
        text = turn.get("text", "")
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def check_evidence(player_input: str, object_properties: dict) -> str:
    """
    Lightweight evidence check (to be moved into evidence_checker.py in Phase 5).

    Python is the source of truth for what physically exists in the room. This
    surfaces the properties of examined objects so the model reasons about REAL
    evidence rather than inventing it. For now it lists the known properties;
    later we'll add claim-to-property matching (VERIFIED / UNVERIFIED flags).
    """
    if not object_properties:
        return "No objects examined yet — nothing to verify against."

    lines = ["Known properties of examined objects:"]
    for obj_id, props in object_properties.items():
        if props:
            prop_str = ", ".join(f"{k}={v}" for k, v in props.items())
            lines.append(f"  - {obj_id}: {prop_str}")
        else:
            lines.append(f"  - {obj_id}: (no notable properties)")
    return "\n".join(lines)


# -- Quick self-test --
# No LLM needed — we build a prompt from a fake game state and print it,
# so you can read exactly what the Gatekeeper would receive.
if __name__ == "__main__":
    fake_state = {
        "scenario": {
            "gatekeeper_role": "Head of Security, Meridian Research Institute",
            "suspicion_context": "Unauthorised access detected at 02:10. Player found near the archive at 02:14.",
            "player_backstory": "The player claims to be a contracted IT auditor on a late-night systems check.",
            "clues": [
                {"id": "obj_audit_letter", "name": "Audit Letter",
                 "detail": "A printed letter dated today, signed by the Director of Operations, authorising a systems audit between 02:00 and 04:00."},
                {"id": "obj_crowbar", "name": "Pry Bar",
                 "detail": "A short steel pry bar leaning by the door frame, which shows two fresh gouges near the lock."},
            ],
        },
        "turn": 4,
        "turns_remaining": 11,
        "player_inventory": ["obj_audit_letter"],
        "examined_objects": ["obj_audit_letter", "obj_crowbar"],
        "object_properties": {
            "obj_audit_letter": {"dated_today": True, "signed_by": "Director of Operations"},
            "obj_crowbar": {"implies_forced_entry": True, "explicable": True},
        },
        "conversation_history": [
            {"role": "player", "text": "I'm the contracted IT auditor. Here's my appointment letter."},
            {"role": "gatekeeper", "text": "The letter looks official, but explain the pry bar."},
        ],
        "player_input": "The pry bar isn't mine — it was already here when I arrived.",
    }

    system, user = build_gatekeeper_prompt(fake_state, persona="suspicious")

    print("=" * 60)
    print("USER PROMPT (this turn):")
    print("=" * 60)
    print(user)

    assert "Head of Security" in user
    assert "Pry Bar" in user
    assert "fresh gouges" in user  # narrative detail made it into the prompt
    print("\n" + "=" * 60)
    print("Prompt assembled correctly, with clue narrative detail included.")