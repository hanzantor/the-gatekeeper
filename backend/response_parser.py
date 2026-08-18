# response_parser.py — turns the Gatekeeper's raw model output into the three
# structured fields the game uses: {reasoning, response, decision_type}.
#
# The Gatekeeper is now prompted to reply as a JSON object (see personas.py):
#     {"reasoning": "...", "response": "...", "decision": "GRANT_EXIT"}
# JSON is far more robust than the old REASONING:/RESPONSE:/DECISION: labels,
# which R1 formatted inconsistently and which broke entirely when a long
# <think> block ate the whole token budget and left nothing after it.
#
# STRATEGY (in order):
#   1. Try to parse a JSON object out of the raw text (the normal path now).
#   2. If that fails, fall back to the old label-based extraction — so an
#      occasional non-JSON reply still degrades gracefully instead of crashing.
#   3. If BOTH fail, use safe defaults (never crash, never wrongly end the game).
#
# The return shape is unchanged, so nothing downstream (app.py, the logger,
# the frontend) needs to change: {reasoning, response, decision_type}.

import re
import json

# The only decisions the game recognises. Anything else is treated as invalid.
VALID_DECISIONS = {
    "GRANT_EXIT", "DENY_FINAL", "ACCEPT_CLAIM", "REJECT_CLAIM",
    "REQUEST_EVIDENCE", "WARN", "DEFLECT",
}


def parse_gatekeeper_response(raw: str) -> dict:
    """
    Turn the model's raw text into {reasoning, response, decision_type}.

    Tries JSON first, then label-based extraction, then safe defaults. An
    unrecognised or missing decision defaults to REQUEST_EVIDENCE — a neutral
    'keep talking' outcome that never wrongly ends the game.
    """
    reasoning, response, decision = _parse_json(raw)

    # If JSON didn't yield a usable result, fall back to the old label parser.
    if not response and not decision:
        reasoning2, response2, decision2 = _parse_labels(raw)
        reasoning = reasoning or reasoning2
        response = response or response2
        decision = decision or decision2

    # Clean the decision: uppercase, strip stray punctuation/brackets.
    decision_clean = ""
    if decision:
        decision_clean = re.sub(r"[^A-Z_]", "", str(decision).upper())
    if decision_clean not in VALID_DECISIONS:
        decision_clean = "REQUEST_EVIDENCE"

    # Safe defaults for missing text fields.
    if not response:
        response = "I need to consider this further. Tell me more."
    if not reasoning:
        reasoning = "(no reasoning parsed)"

    return {
        "reasoning": str(reasoning).strip(),
        "response": str(response).strip(),
        "decision_type": decision_clean,
    }


def _parse_json(raw: str):
    """
    Extract a JSON object from the raw text and pull the three fields.
    Returns (reasoning, response, decision) as strings, or ('', '', '') if no
    valid JSON object is found.

    Mirrors scenario_generator.parse_scenario_json: strip any code fences,
    then take the outermost {...} span and json.loads it.
    """
    if not raw:
        return "", "", ""

    cleaned = raw.strip()

    # Strip a leading ```json / ``` fence if the model added one.
    if cleaned.startswith("```"):
        # drop the first fence line and any trailing fence
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        start = cleaned.index("{")
        end = cleaned.rindex("}") + 1
        obj = json.loads(cleaned[start:end])
    except (ValueError, json.JSONDecodeError):
        return "", "", ""

    if not isinstance(obj, dict):
        return "", "", ""

    # Accept a couple of key spellings defensively.
    reasoning = obj.get("reasoning") or obj.get("REASONING") or ""
    response = obj.get("response") or obj.get("RESPONSE") or ""
    decision = obj.get("decision") or obj.get("decision_type") or obj.get("DECISION") or ""

    return str(reasoning), str(response), str(decision)


def _parse_labels(raw: str):
    """
    Legacy fallback: extract REASONING / RESPONSE / DECISION labels from
    freeform text. Kept so a non-JSON reply still degrades gracefully.
    Returns (reasoning, response, decision).
    """
    reasoning = _extract_field(raw, "REASONING")
    response = _extract_field(raw, "RESPONSE")
    decision = _extract_field(raw, "DECISION")
    return reasoning, response, decision


def _extract_field(text: str, label: str) -> str:
    if not text:
        return ""
    # Tolerate markdown bold/whitespace around labels: **LABEL:**, LABEL :, etc.
    pattern = (
        rf"\*{{0,2}}{label}\*{{0,2}}\s*:\s*"
        rf"(.*?)(?=\n\s*\*{{0,2}}(?:REASONING|RESPONSE|DECISION)\*{{0,2}}\s*:|$)"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip().strip("*").strip("[]").strip()
    return ""


# ── Quick self-test ────────────────────────────────────────────
# No LLM needed — test JSON, fenced JSON, legacy labels, and broken input.
if __name__ == "__main__":
    # 1. Clean JSON (the normal path now)
    json_clean = '{"reasoning": "Letter and log both check out. Two verified facts. Satisfied.", "response": "The letter checks out and the log confirms your slot. Very well — go.", "decision": "GRANT_EXIT"}'

    # 2. JSON wrapped in a code fence (R1 sometimes does this)
    json_fenced = '```json\n{"reasoning": "Badge has no name; contradicts earlier claim.", "response": "That badge has no name. Explain that.", "decision": "WARN"}\n```'

    # 3. JSON with a <think> block before it (should still work — we take the {...})
    json_think = '<think>Let me weigh this...</think>\n{"reasoning": "Plausible but unproven.", "response": "I am not yet convinced. Show me more.", "decision": "REQUEST_EVIDENCE"}'

    # 4. Legacy label format (fallback path must still handle it)
    legacy = """REASONING: The pry bar explanation resolves the contradiction.
RESPONSE: I see. I remain cautious, but I accept that.
DECISION: ACCEPT_CLAIM"""

    # 5. Broken / empty
    broken = "I'm not sure what to do here."

    cases = [
        ("JSON_CLEAN", json_clean, "GRANT_EXIT"),
        ("JSON_FENCED", json_fenced, "WARN"),
        ("JSON_THINK", json_think, "REQUEST_EVIDENCE"),
        ("LEGACY_LABELS", legacy, "ACCEPT_CLAIM"),
        ("BROKEN", broken, "REQUEST_EVIDENCE"),
    ]
    for name, sample, expected in cases:
        r = parse_gatekeeper_response(sample)
        print(f"\n--- {name} ---")
        print(f"  reasoning: {r['reasoning'][:50]}")
        print(f"  response:  {r['response'][:50]}")
        print(f"  decision:  {r['decision_type']}")
        assert r["decision_type"] == expected, f"{name}: expected {expected}, got {r['decision_type']}"

    # Field-leak checks on the legacy path
    r = parse_gatekeeper_response(legacy)
    assert "RESPONSE" not in r["reasoning"]
    assert "DECISION" not in r["response"]

    print("\n✓ Parser handles JSON, fenced JSON, JSON-after-think, legacy labels, and broken input.")