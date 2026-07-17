# response_parser.py — extracts the three structured fields from the
# Gatekeeper's raw text output.
#
# Every persona is instructed to reply in this exact format:
#     REASONING: ...
#     RESPONSE: ...
#     DECISION: ...
# This file turns that text into a clean dict. It is deliberately forgiving:
# LLMs don't always format perfectly, so a parse failure must NEVER crash
# the game — it falls back to safe defaults instead.

import re

# The only decisions the game recognises. Anything else is treated as invalid.
VALID_DECISIONS = {
    "GRANT_EXIT", "DENY_FINAL", "ACCEPT_CLAIM", "REJECT_CLAIM",
    "REQUEST_EVIDENCE", "WARN", "DEFLECT",
}


def parse_gatekeeper_response(raw: str) -> dict:
    """
    Turn the model's raw text into {reasoning, response, decision_type}.

    Forgiving by design:
    - tolerates different capitalisation and spacing of the labels
    - if a field is missing, uses a safe default
    - if the decision isn't one of the valid set, defaults to REQUEST_EVIDENCE
      (a neutral 'keep talking' outcome that never wrongly ends the game)
    """
    reasoning = _extract_field(raw, "REASONING")
    response = _extract_field(raw, "RESPONSE")
    decision = _extract_field(raw, "DECISION")

    # Clean up the decision: uppercase, strip stray punctuation/brackets.
    decision_clean = ""
    if decision:
        decision_clean = re.sub(r"[^A-Z_]", "", decision.upper())

    # Validate against the known set; fall back if unrecognised.
    if decision_clean not in VALID_DECISIONS:
        decision_clean = "REQUEST_EVIDENCE"

    # Safe defaults for missing text fields.
    if not response:
        response = "I need to consider this further. Tell me more."
    if not reasoning:
        reasoning = "(no reasoning parsed)"

    return {
        "reasoning": reasoning.strip(),
        "response": response.strip(),
        "decision_type": decision_clean,
    }


def _extract_field(text: str, label: str) -> str:
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
# No LLM needed — we test against sample outputs, including messy ones.
if __name__ == "__main__":
    # 1. A well-formatted response
    good = """REASONING: The player showed a signed letter and the access log matches. Two verified claims. I am satisfied.
RESPONSE: The letter checks out and the log confirms your slot. Very well — I'll open the door.
DECISION: GRANT_EXIT"""

    # 2. A messy one: lowercase labels, brackets, extra whitespace
    messy = """reasoning:  [The badge has no name and contradicts their earlier claim.]
response: That badge has no name on it. Explain that.
decision: [WARN]"""

    # 3. A broken one: no DECISION line at all
    broken = """REASONING: Unclear situation.
RESPONSE: I'm not sure I believe you."""

# 4. R1's markdown-bold labels — the real-world case
    bolded = """**REASONING:** The pry bar explanation resolves the contradiction but concerns remain.
**RESPONSE:** I see you now explain the pry bar. I remain cautious.
**DECISION:** ACCEPT_CLAIM"""

    for label, sample in [("GOOD", good), ("MESSY", messy), ("BROKEN", broken), ("BOLDED", bolded)]:
        result = parse_gatekeeper_response(sample)
        print(f"\n--- {label} ---")
        print(f"  reasoning: {result['reasoning'][:50]}...")
        print(f"  response:  {result['response'][:50]}...")
        print(f"  decision:  {result['decision_type']}")

    # Assert the fallbacks worked as intended
    assert parse_gatekeeper_response(good)["decision_type"] == "GRANT_EXIT"
    assert parse_gatekeeper_response(messy)["decision_type"] == "WARN"
    assert parse_gatekeeper_response(broken)["decision_type"] == "REQUEST_EVIDENCE"
    assert parse_gatekeeper_response(bolded)["decision_type"] == "ACCEPT_CLAIM"
    r = parse_gatekeeper_response(bolded)
    assert "RESPONSE" not in r["reasoning"], "reasoning leaked into next field"
    assert "DECISION" not in r["response"], "decision leaked into response"
    print("\n✓ Parser handles clean, messy, and broken responses correctly.")