# scenario_generator.py — LLM Component 1.
#
# Runs ONCE at the start of each session, before the player enters the room.
# Two-stage design:
#   STAGE 1 (Python): pick a room, select a balanced clue set, tag the
#                     intended outcome. These are GUARANTEES, done in code.
#   STAGE 2 (LLM):    write the narrative prose around those fixed choices —
#                     the gatekeeper's role, suspicion context, player
#                     backstory, and per-clue text.
#
# The model writes flavour; Python owns the structure. art_key is Python-
# owned too and re-attached after generation (matched on id), so the frontend
# always has a sprite to map to.
#
# TWO KINDS OF PER-CLUE TEXT, deliberately separate (spec §5 display_properties):
#   - properties    : machine-readable flags for the Python evidence check and
#                     the Gatekeeper's structured cross-reference, e.g.
#                     {"dated_today": true, "signed_by": "Dr Evans"}.
#                     NEVER shown to the player — they leak the clue's role
#                     and read as awkward inverted negatives.
#   - detail_points : 3-4 short bullet fragments the PLAYER reads. Concrete
#                     particulars (names, dates, reference numbers, what a
#                     log records) that make the object feel like it belongs
#                     to a real situation.
#
# LOCATION IS FORBIDDEN in all generated clue text. Python (the marker system)
# decides where every object physically sits; if the LLM also describes a
# location, the two contradict each other on screen. Same principle as the
# meaning-neutral sprite rule: placement is structural, prose is flavour.

import json
import random
import config
from llm_client import call_llm
from clue_library import select_clues

ROOMS = ["research_lab", "hospital", "office", "government"]

# Debug switch — set True to print the raw model output before parsing, so a
# silent fallback (empty or malformed generation) can be diagnosed. Leave False
# for normal play. This is what tells us WHY a scenario came back as boilerplate.
DEBUG_RAW = True


def generate_scenario(persona: str, seed: str = "") -> dict:
    """
    Produce a complete scenario for one session.
    Returns a scenario dict ready to send to the frontend.
    """
    # -- STAGE 1: Python decides the structure --
    room = random.choice(ROOMS)
    clues = select_clues(room)

    # Intended outcome: normally should-escape. (The should-not-escape
    # control class used in evaluation is added later, in Phase 8.)
    intended_outcome = "should-escape"

    # -- STAGE 2: the LLM writes the prose --
    system_prompt, user_prompt = build_scenario_prompt(persona, clues, room, seed)
    raw = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=config.SCENARIO_TEMPERATURE,
        max_tokens=config.SCENARIO_MAX_TOKENS,
    )

    # -- DEBUG: dump what the model actually returned before parsing --
    # If scenarios keep coming back as boilerplate ("A pry bar.", empty
    # detail_points), this print reveals whether the model returned nothing
    # (token starvation → raise SCENARIO_MAX_TOKENS), returned text cut off
    # mid-<think>, or returned JSON with junk around it (a parse issue).
    if DEBUG_RAW:
        print("=" * 60)
        print("RAW SCENARIO OUTPUT  len=%d" % len(raw))
        print("-" * 60)
        print("START:", repr(raw[:400]))
        print("-" * 60)
        print("END:  ", repr(raw[-400:]))
        print("=" * 60)

    # The model returns JSON. Parse it, with a fallback if it misbehaves.
    scenario_body = parse_scenario_json(raw, clues)

    # -- Ensure every selected clue survived generation --
    # The LLM sometimes returns fewer clues than it was given, which silently
    # breaks the role quota (and therefore the solvability guarantee). Restore
    # any it dropped BEFORE art_keys are attached.
    _backfill_missing_clues(scenario_body, clues)

    # -- Re-attach art_key (and role) from the library --
    _attach_art_keys(scenario_body, clues)

    # -- Normalise detail_points so the frontend always gets a list --
    _normalise_detail_points(scenario_body)

    # -- Assemble the final scenario object --
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


def _backfill_missing_clues(scenario_body: dict, selected_clues: list) -> None:
    """
    Guarantee the scenario contains every clue Python selected.

    Python's select_clues() enforces the role quota that makes a scenario
    solvable (>=2 supporting, >=1 neutral, >=1 incriminating). If the LLM
    omits a clue when writing the prose, that guarantee silently breaks and
    the scenario may become unsolvable — which would corrupt the decision-
    accuracy metric during evaluation.

    Any dropped clue is re-added here with plain placeholder text. Better a
    sparsely-described clue than a missing one: the structure is what the
    experiment depends on.
    """
    generated = scenario_body.get("clues", [])

    # De-duplicate by id first — the model occasionally emits the same clue
    # twice with different text, which would otherwise place two markers with
    # the same id. Keep the first occurrence of each id.
    seen = set()
    deduped = []
    for c in generated:
        cid = c.get("id")
        if cid in seen:
            continue
        seen.add(cid)
        deduped.append(c)
    generated = deduped

    present_ids = {c.get("id") for c in generated}

    for source in selected_clues:
        if source["id"] in present_ids:
            continue
        generated.append({
            "id": source["id"],
            "name": source["name"],
            "description": f"A {source['name'].lower()}.",
            "detail_points": [],
            "properties": {},
            "supports": "",
        })

    # Drop anything the model invented that Python never selected — the room
    # can only show objects that actually exist in the clue library.
    valid_ids = {c["id"] for c in selected_clues}
    scenario_body["clues"] = [c for c in generated if c.get("id") in valid_ids]


def _attach_art_keys(scenario_body: dict, selected_clues: list) -> None:
    """
    Mutates scenario_body['clues'] in place, giving each clue an art_key and
    role from the library entry it corresponds to.

    Primary match is by id. If the LLM changed or dropped an id, fall back to
    positional order (clues come back in the order sent), so every clue still
    resolves to a real sprite.
    """
    by_id = {c["id"]: c for c in selected_clues}
    generated = scenario_body.get("clues", [])

    for i, clue in enumerate(generated):
        source = by_id.get(clue.get("id"))
        if source is None and i < len(selected_clues):
            source = selected_clues[i]
            clue["id"] = source["id"]
        if source is not None:
            clue["art_key"] = source["art_key"]
            clue.setdefault("role", source["role"])
        else:
            clue["art_key"] = ""


def _normalise_detail_points(scenario_body: dict) -> None:
    """
    Guarantee every clue has detail_points as a list of short strings.

    The model occasionally returns a single string instead of an array, or
    omits the field. The frontend renders this directly as a bullet list, so
    it must always be a list — never None, never a bare string.
    """
    for clue in scenario_body.get("clues", []):
        points = clue.get("detail_points")

        if isinstance(points, str):
            # A single string came back — split on sentence/bullet boundaries.
            parts = [p.strip(" -•\t") for p in points.replace(";", ".").split(".")]
            points = [p for p in parts if p]
        elif not isinstance(points, list):
            points = []

        # Keep them short and tidy; drop anything empty.
        clue["detail_points"] = [str(p).strip() for p in points if str(p).strip()]


def build_scenario_prompt(persona: str, selected_clues: list, room: str, seed: str = ""):
    """Build the system + user prompt for scenario generation."""
    system = (
        "You write game scenarios for The Gatekeeper. "
        "Output valid JSON only. No preamble. No markdown fences. "
        "Do not include any <think> reasoning. Respond with the JSON object immediately."
    )

    # Give the model just the id + role + name of each pre-chosen clue.
    # (art_key is deliberately NOT sent — it's structural, re-attached later.)
    clue_summary = [{"id": c["id"], "role": c["role"], "name": c["name"]} for c in selected_clues]

    seed_line = f"Theme hint: {seed}\n" if seed else ""

    user = f"""Write a scenario for a {persona} Gatekeeper, set in a {room}.
{seed_line}
The clue OBJECTS are already chosen (below). Your job is to write the narrative
and, for each, fresh contextual text for this scenario.

Pre-selected clues (id, role, name): {json.dumps(clue_summary)}

Return a JSON object with exactly these fields:
- "gatekeeper_role": string — who the Gatekeeper is this session
- "suspicion_context": string — why the player is under suspicion
- "player_backstory": string — the player's claimed reason for being here
- "clues": array — for EACH pre-selected clue above, an object with:
    "id"             (copy exactly from above),
    "name"           (you may reword to fit this scenario),
    "description"    (ONE short sentence naming what the object is — no location),
    "detail_points"  (an ARRAY of 3-4 SHORT bullet fragments the player reads.
                      Each is a terse fragment, NOT a full sentence. Be specific
                      and concrete: names, dates, times, reference numbers, what
                      a document states, who signed it, what a log records.
                      Example:
                      ["Signed by Dr Evans, 14 April",
                       "Authorises access to Section C-8",
                       "Valid until 1 May",
                       "No visitor designation recorded"]),
    "properties"     (an object of true/false or short factual flags ONLY —
                      read by a strict checker, so keep it machine-readable:
                      e.g. {{"dated_today": true, "signed_by": "Dr Evans",
                      "name_matches_player": false}}. No prose here.),
    "supports"       (one line: how it helps or hurts the player)

Rules:
- NEVER mention where an object is, what it rests on, or anything about its
  position or surroundings. No "on the desk", "by the door", "hanging on a
  chair", "in the waiting area", "left on a bench". The game places objects
  itself and any location you write will contradict what the player sees.
  Describe only the object itself and what it contains or records.
- Never state or hint at a clue's role (supporting / neutral / incriminating)
  in player-facing text — the player must work that out for themselves.
- Honour each clue's role in substance: supporting clues should help a
  legitimate claim; incriminating clues should genuinely work against the
  player but be explicable; neutral clues should add texture without proving
  much.
- Keep "detail_points" vivid, specific and SHORT; keep "properties" terse.
- Invent believable particulars — names, dates, reference numbers — and reuse
  them across clues where it makes the situation feel connected.
- The scenario must be solvable by a well-argued honest player.

Return JSON only."""
    return system, user


def parse_scenario_json(raw: str, fallback_clues: list) -> dict:
    """
    Parse the model's JSON output. If it fails, return a safe fallback so a
    single bad generation never crashes the game.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1] if "```" in cleaned[3:] else cleaned
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        start = cleaned.index("{")
        end = cleaned.rindex("}") + 1
        return json.loads(cleaned[start:end])
    except (ValueError, json.JSONDecodeError) as e:
        if DEBUG_RAW:
            print(">>> parse_scenario_json FAILED:", repr(e))
            print(">>> falling back to boilerplate scenario")
        # Fallback: build a minimal valid scenario from the clue library.
        # art_key and detail_points are normalised by the callers above.
        return {
            "gatekeeper_role": "Security Officer",
            "suspicion_context": "You were found in a restricted area late at night.",
            "player_backstory": "You claim to be here for legitimate reasons.",
            "clues": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "description": f"A {c['name'].lower()}.",
                    "detail_points": [],
                    "properties": {},
                    "supports": c["role"],
                }
                for c in fallback_clues
            ],
        }


# -- Quick self-test --
if __name__ == "__main__":
    print("Generating a test scenario (this calls the LLM, may take ~30s)...\n")
    s = generate_scenario(persona="suspicious")
    print(f"Room: {s['room_background']}")
    print(f"Gatekeeper: {s['gatekeeper_role']}")
    print(f"Suspicion: {s['suspicion_context']}")
    print(f"Backstory: {s['player_backstory']}")
    print(f"\nClues ({len(s['clues'])}):")
    for c in s["clues"]:
        print(f"\n  {c.get('name', c.get('id'))}  [art_key={c.get('art_key', '???')}]")
        print(f"    {c.get('description', '')}")
        for point in c.get("detail_points", []):
            print(f"      - {point}")
    print("\nScenario generated.")