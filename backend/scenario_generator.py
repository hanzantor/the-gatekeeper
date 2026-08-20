# scenario_generator.py: LLM Component 1. Runs once per session before the player enters.
# Stage 1 (Python): pick room, select balanced clues, tag outcome — these are guarantees.
# Stage 2 (LLM): write the prose around those fixed choices.
# art_key is Python-owned and re-attached after generation (matched on id).
#
# Two kinds of per-clue text, kept separate:
#   properties    : machine-readable flags for the evidence check. Never shown to the player.
#   detail_points : 3-4 short fragments the player reads (names, dates, reference numbers).
# Location is banned in all generated text — Python's marker system places objects, not the model.

import json
import random
import config
from llm_client import call_llm
from clue_library import select_clues

ROOMS = ["research_lab", "hospital", "office", "government"]

# set True to print raw model output before parsing (diagnoses silent fallbacks); False for the demo
DEBUG_RAW = True


def generate_scenario(persona: str, seed: str = "") -> dict:
    # Stage 1: Python decides the structure
    room = random.choice(ROOMS)
    clues = select_clues(room)

    # normally should-escape; the should-not-escape control comes in evaluation
    intended_outcome = "should-escape"

    # Stage 2: the LLM writes the prose
    system_prompt, user_prompt = build_scenario_prompt(persona, clues, room, seed)
    raw = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=config.SCENARIO_TEMPERATURE,
        max_tokens=config.SCENARIO_MAX_TOKENS,
    )

    # dump what the model actually returned — len=0 means token starvation, not a parse issue
    if DEBUG_RAW:
        print("=" * 60)
        print("RAW SCENARIO OUTPUT  len=%d" % len(raw))
        print("-" * 60)
        print("START:", repr(raw[:400]))
        print("-" * 60)
        print("END:  ", repr(raw[-400:]))
        print("=" * 60)

    scenario_body = parse_scenario_json(raw, clues)

    # restore any clue the model dropped BEFORE art_keys are attached (keeps the quota intact)
    _backfill_missing_clues(scenario_body, clues)

    # re-attach art_key + role from the library
    _attach_art_keys(scenario_body, clues)

    # make sure detail_points is always a list for the frontend
    _normalise_detail_points(scenario_body)

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
    # Guarantee every clue Python selected survives. A dropped clue silently breaks the
    # solvability quota, which would corrupt the decision-accuracy metric in evaluation.
    generated = scenario_body.get("clues", [])

    # dedupe by id first — the model sometimes emits the same clue twice, which would
    # place two markers with the same id. Keep the first occurrence.
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

    # drop anything the model invented — the room can only show real library objects
    valid_ids = {c["id"] for c in selected_clues}
    scenario_body["clues"] = [c for c in generated if c.get("id") in valid_ids]


def _attach_art_keys(scenario_body: dict, selected_clues: list) -> None:
    # give each clue its art_key + role from the library. Match on id; fall back to
    # position if the model changed an id, so every clue still resolves to a real sprite.
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
    # detail_points must always be a list of short strings — the frontend renders it as bullets
    for clue in scenario_body.get("clues", []):
        points = clue.get("detail_points")

        if isinstance(points, str):
            # a single string came back — split it into fragments
            parts = [p.strip(" -•\t") for p in points.replace(";", ".").split(".")]
            points = [p for p in parts if p]
        elif not isinstance(points, list):
            points = []

        clue["detail_points"] = [str(p).strip() for p in points if str(p).strip()]


def build_scenario_prompt(persona: str, selected_clues: list, room: str, seed: str = ""):
    system = (
        "You write game scenarios for The Gatekeeper. "
        "Output valid JSON only. No preamble. No markdown fences. "
        "Do not include any <think> reasoning. Respond with the JSON object immediately."
    )

    # send only id + role + name — art_key is structural and re-attached later
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
    # JSON-first with a safe fallback, so one bad generation never crashes the game
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
        # minimal valid scenario built straight from the clue library
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