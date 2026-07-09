# scenario_generator.py — LLM Component 1.
#
# Runs ONCE at the start of each session, before the player enters the room.
# Two-stage design:
#   STAGE 1 (Python): pick a room, select a balanced clue set, tag the
#                     intended outcome. These are GUARANTEES, done in code.
#   STAGE 2 (LLM):    write the narrative prose around those fixed choices —
#                     the gatekeeper's role, suspicion context, player
#                     backstory, and a description + properties per clue.
#
# The model writes flavour; Python owns the structure. That's what keeps
# every scenario solvable and fair.

import json
import random
import config
from llm_client import call_llm
from clue_library import select_clues

ROOMS = ["research_lab", "hospital", "office", "government"]


def generate_scenario(persona: str, seed: str = "") -> dict:
    """
    Produce a complete scenario for one session.
    Returns a scenario dict ready to send to the frontend.
    """
    # ── STAGE 1: Python decides the structure ──────────────────
    room = random.choice(ROOMS)
    clues = select_clues(room)

    # Intended outcome: normally should-escape. (The should-not-escape
    # control class used in evaluation is added later, in Phase 8.)
    intended_outcome = "should-escape"

    # ── STAGE 2: the LLM writes the prose ──────────────────────
    system_prompt, user_prompt = build_scenario_prompt(persona, clues, room, seed)
    raw = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=config.SCENARIO_TEMPERATURE,
    )

    # The model returns JSON. Parse it, with a fallback if it misbehaves.
    scenario_body = parse_scenario_json(raw, clues)

    # ── Assemble the final scenario object ─────────────────────
    scenario = {
        "scenario_id": f"scenario_{random.randint(10000, 99999)}",
        "room_background": room,
        "intended_outcome": intended_outcome,
        "persona": persona,
        "gatekeeper_role": scenario_body.get("gatekeeper_role", "Security Officer"),
        "suspicion_context": scenario_body.get("suspicion_context", "You were found in a restricted area."),
        "player_backstory": scenario_body.get("player_backstory", "You claim to have legitimate business here."),
        "clues": scenario_body.get("clues", []),
    }
    return scenario


def build_scenario_prompt(persona: str, selected_clues: list, room: str, seed: str = ""):
    """Build the system + user prompt for scenario generation."""
    system = (
        "You write game scenarios for The Gatekeeper. "
        "Output valid JSON only. No preamble. No markdown fences."
    )

    # Give the model just the id + role of each pre-chosen clue.
    clue_summary = [{"id": c["id"], "role": c["role"], "name": c["name"]} for c in selected_clues]

    seed_line = f"Theme hint: {seed}\n" if seed else ""

    user = f"""Write a scenario for a {persona} Gatekeeper, set in a {room}.
{seed_line}
The clue OBJECTS are already chosen (below). Your job is to write the narrative
and a fresh description + properties for each, contextualised to this scenario.

Pre-selected clues (id, role, name): {json.dumps(clue_summary)}

Return a JSON object with exactly these fields:
- "gatekeeper_role": string — who the Gatekeeper is this session
- "suspicion_context": string — why the player is under suspicion
- "player_backstory": string — the player's claimed reason for being here
- "clues": array — for EACH pre-selected clue above, an object with:
    "id" (copy exactly from above),
    "name" (you may reword),
    "description" (1-2 sentences describing the object),
    "properties" (an object of true/false or short facts about it),
    "supports" (one line: how it helps or hurts the player)

Rules:
- Honour each clue's role: supporting clues should help a legitimate claim;
  incriminating clues should genuinely work against the player but be explicable;
  neutral clues should add atmosphere without proving much.
- The scenario must be solvable by a well-argued honest player.
- Keep it grounded and believable.

Return JSON only."""
    return system, user


def parse_scenario_json(raw: str, fallback_clues: list) -> dict:
    """
    Parse the model's JSON output. If it fails, return a safe fallback so a
    single bad generation never crashes the game.
    """
    # Models sometimes wrap JSON in ```json fences despite instructions — strip them.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1] if "```" in cleaned[3:] else cleaned
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        # Find the outermost { } in case there's stray text around it.
        start = cleaned.index("{")
        end = cleaned.rindex("}") + 1
        return json.loads(cleaned[start:end])
    except (ValueError, json.JSONDecodeError):
        # Fallback: build a minimal valid scenario from the clue library.
        return {
            "gatekeeper_role": "Security Officer",
            "suspicion_context": "You were found in a restricted area late at night.",
            "player_backstory": "You claim to be here for legitimate reasons.",
            "clues": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "description": f"A {c['name'].lower()} found in the room.",
                    "properties": {},
                    "supports": c["role"],
                }
                for c in fallback_clues
            ],
        }


# ── Quick self-test ────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating a test scenario (this calls the LLM, may take ~30s)...\n")
    s = generate_scenario(persona="suspicious")
    print(f"Room: {s['room_background']}")
    print(f"Gatekeeper: {s['gatekeeper_role']}")
    print(f"Suspicion: {s['suspicion_context']}")
    print(f"Backstory: {s['player_backstory']}")
    print(f"\nClues ({len(s['clues'])}):")
    for c in s["clues"]:
        print(f"  • {c.get('name', c.get('id'))}: {c.get('description', '')}")
    print("\n✓ Scenario generated.")
