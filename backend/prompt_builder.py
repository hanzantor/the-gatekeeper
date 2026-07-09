# prompt_builder.py — assembles the single prompt the Gatekeeper reasons over
# each turn. This is the connective tissue of the agent: it gathers the
# persona, the scenario, the live game state, the memory window, and the
# evidence check into one instruction, then hands back (system, user) prompts.

import config
from personas import PERSONA_PROMPTS


def build_gatekeeper_prompt(game_state: dict, persona: str) -> tuple[str, str]:
    """
    Build the (system_prompt, user_prompt) pair for one Gatekeeper turn.

    - system_prompt: the persona definition (fetched from personas.py)
    - user_prompt:   everything specific to THIS turn — scenario, state,
                     memory, evidence, and the player's latest input
    """
    system_prompt = PERSONA_PROMPTS[persona]

    scenario = game_state["scenario"]

    # Run the factual evidence check (Python is the source of truth here).
    evidence_flags = check_evidence(
        game_state.get("player_input", ""),
        game_state.get("object_properties", {}),
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

EVIDENCE CHECK:
{evidence_flags}

CONVERSATION HISTORY:
{format_history(windowed)}

PLAYER JUST SAID:
"{game_state.get('player_input', '')}"

Before responding, check the player's latest claim against BOTH the physical
evidence AND everything they have said earlier. If it contradicts the evidence
or a prior statement, surface that. If new evidence or a sound argument now
vindicates an earlier doubt, update in their favour — but only when genuinely
warranted, not merely because they insisted.

Respond as the Gatekeeper. Reason first, then respond.
If the player has made a convincing case — given your character, this scenario,
and the evidence — grant exit. Do not grant exit unless you genuinely judge it is deserved."""

    return system_prompt, user_prompt


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


# ── Quick self-test ────────────────────────────────────────────
# No LLM needed — we build a prompt from a fake game state and print it,
# so you can read exactly what the Gatekeeper would receive.
if __name__ == "__main__":
    fake_state = {
        "scenario": {
            "gatekeeper_role": "Head of Security, Meridian Research Institute",
            "suspicion_context": "Unauthorised access detected at 02:10. Player found near the archive at 02:14.",
            "player_backstory": "The player claims to be a contracted IT auditor on a late-night systems check.",
        },
        "turn": 4,
        "turns_remaining": 11,
        "player_inventory": ["obj_audit_letter", "obj_access_log"],
        "examined_objects": ["obj_audit_letter", "obj_visitor_badge", "obj_crowbar"],
        "object_properties": {
            "obj_audit_letter": {"dated_today": True, "signed_by": "Director of Operations"},
            "obj_visitor_badge": {"dated_today": True, "no_name": True},
            "obj_crowbar": {"implies_forced_entry": True, "explicable": True},
        },
        "conversation_history": [
            {"role": "player", "text": "I'm the contracted IT auditor. Here's my appointment letter."},
            {"role": "gatekeeper", "text": "The letter looks official, but that badge has no name. Explain."},
        ],
        "player_input": "Check the access log — I'm listed as scheduled for tonight.",
    }

    system, user = build_gatekeeper_prompt(fake_state, persona="suspicious")

    print("=" * 60)
    print("SYSTEM PROMPT (persona):")
    print("=" * 60)
    print(system[:200] + "...\n")
    print("=" * 60)
    print("USER PROMPT (this turn):")
    print("=" * 60)
    print(user)

    # Sanity checks
    assert "Head of Security" in user
    assert "access log" in user.lower()
    assert "obj_crowbar" in user
    print("\n" + "=" * 60)
    print("✓ Prompt assembled correctly with all pieces in place.")