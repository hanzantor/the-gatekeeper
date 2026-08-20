# response_parser.py: turns the Gatekeeper's raw model output into the three fields

import re
import json

# the only decisions the game recognises — anything else is treated as invalid
VALID_DECISIONS = {
    "GRANT_EXIT", "DENY_FINAL", "ACCEPT_CLAIM", "REJECT_CLAIM",
    "REQUEST_EVIDENCE", "WARN", "DEFLECT",
}


def parse_gatekeeper_response(raw: str) -> dict:
    # JSON first, then labels, then safe defaults. A missing/invalid decision defaults
    # to REQUEST_EVIDENCE — a neutral "keep talking" that never wrongly ends the game.
    reasoning, response, decision = _parse_json(raw)

    if not response and not decision:
        reasoning2, response2, decision2 = _parse_labels(raw)
        reasoning = reasoning or reasoning2
        response = response or response2
        decision = decision or decision2

    # clean the decision token: uppercase, strip stray punctuation/brackets
    decision_clean = ""
    if decision:
        decision_clean = re.sub(r"[^A-Z_]", "", str(decision).upper())
    if decision_clean not in VALID_DECISIONS:
        decision_clean = "REQUEST_EVIDENCE"

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
    # take the outermost {...} and json.loads it — skips past any <think> block or fence
    # the model put before/around the JSON. Same technique as the scenario generator.
    if not raw:
        return "", "", ""

    cleaned = raw.strip()

    if cleaned.startswith("```"):
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

    # accept a couple of key spellings defensively
    reasoning = obj.get("reasoning") or obj.get("REASONING") or ""
    response = obj.get("response") or obj.get("RESPONSE") or ""
    decision = obj.get("decision") or obj.get("decision_type") or obj.get("DECISION") or ""

    return str(reasoning), str(response), str(decision)


def _parse_labels(raw: str):
    # legacy fallback: pull REASONING/RESPONSE/DECISION labels from freeform text
    reasoning = _extract_field(raw, "REASONING")
    response = _extract_field(raw, "RESPONSE")
    decision = _extract_field(raw, "DECISION")
    return reasoning, response, decision


def _extract_field(text: str, label: str) -> str:
    if not text:
        return ""
    # tolerate bold/whitespace around labels: **LABEL:**, LABEL :, etc.
    pattern = (
        rf"\*{{0,2}}{label}\*{{0,2}}\s*:\s*"
        rf"(.*?)(?=\n\s*\*{{0,2}}(?:REASONING|RESPONSE|DECISION)\*{{0,2}}\s*:|$)"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip().strip("*").strip("[]").strip()
    return ""