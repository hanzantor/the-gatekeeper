# app.py — the Flask web server: the front door of the backend.
#
# The React frontend talks to the backend ONLY through these HTTP endpoints.
# Each endpoint routes a request to the logic we've already built.
#
# Endpoints:
#   GET  /api/health        — confirms the server is running
#   POST /api/scenario      — generates a fresh scenario, starts a session log
#   POST /api/gatekeeper    — runs one Gatekeeper turn, logs it
#   GET  /api/logs/<id>     — returns a session log as JSON
#
# SESSION LOGGING (spec §17): logging is backend-driven so it captures the
# Gatekeeper's `reasoning`, which never reaches the frontend and is the centre
# of the coherence metric. /api/scenario mints a session_id and returns it;
# the frontend echoes it back on every /api/gatekeeper call so turns attach to
# the right session.

from flask import Flask, request, jsonify
from flask_cors import CORS

import config
from scenario_generator import generate_scenario
from prompt_builder import build_gatekeeper_prompt, check_evidence
from llm_client import call_llm
from response_parser import parse_gatekeeper_response
from session_logger import logger

app = Flask(__name__)
CORS(app)  # lets the React frontend (a different port) call this backend


@app.route("/api/health", methods=["GET"])
def health():
    """Simple check the frontend uses to confirm the backend is up."""
    return jsonify({"status": "ok", "model": config.ACTIVE_MODEL})


@app.route("/api/scenario", methods=["POST"])
def scenario():
    """
    Generate a fresh scenario for a new session, and open its log.
    Expects JSON: { "persona": "suspicious", "seed": "optional",
                    "player_type": "optional" }
    Returns the scenario JSON with a `session_id` added.
    """
    data = request.get_json(force=True) or {}
    persona = data.get("persona", "fair")
    seed = data.get("seed", "")
    player_type = data.get("player_type", "human")

    if persona not in ("suspicious", "fair", "corruptible"):
        return jsonify({"error": f"Unknown persona: {persona}"}), 400

    try:
        result = generate_scenario(persona=persona, seed=seed)
        # Open a session log and hand the id back to the client, which will
        # echo it on every subsequent /api/gatekeeper call.
        session_id = logger.start_session(
            persona=persona,
            scenario=result,
            model=config.ACTIVE_MODEL,
            player_type=player_type,
        )
        result["session_id"] = session_id
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Scenario generation failed: {e}"}), 500


@app.route("/api/gatekeeper", methods=["POST"])
def gatekeeper():
    """
    Run one Gatekeeper turn and log it.
    Expects the full game state JSON (see prompt_builder for the shape),
    including the `session_id` returned by /api/scenario.
    Returns: { reasoning, response, decision_type, turn, scenario_id }

    On a final turn the decision is forced to DENY_FINAL server-side (spec
    §12), regardless of what the model emitted. When the decision ends the
    game (GRANT_EXIT or DENY_FINAL), the session log is closed.
    """
    game_state = request.get_json(force=True) or {}
    persona = game_state.get("persona", "fair")
    session_id = game_state.get("session_id", "")

    if persona not in ("suspicious", "fair", "corruptible"):
        return jsonify({"error": f"Unknown persona: {persona}"}), 400

    try:
        system_prompt, user_prompt = build_gatekeeper_prompt(game_state, persona)
        raw = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=config.GATEKEEPER_TEMPERATURE,
        )
        parsed = parse_gatekeeper_response(raw)

        # On the final turn, the outcome is fixed: the door stays shut.
        if game_state.get("final_turn"):
            parsed["decision_type"] = "DENY_FINAL"

        parsed["turn"] = game_state.get("turn", 1)
        parsed["scenario_id"] = game_state.get("scenario", {}).get("scenario_id", "")

        # ── Log this turn ──────────────────────────────────────
        # Recompute the evidence string the prompt used (cheap, pure) so the
        # log records exactly what the Gatekeeper reasoned against.
        evidence_result = check_evidence(
            game_state.get("player_input", ""),
            game_state.get("object_properties", {}),
        )
        logger.log_turn(
            session_id,
            player_input=game_state.get("player_input", ""),
            examined_objects=game_state.get("examined_objects", []),
            evidence_result=evidence_result,
            reasoning=parsed["reasoning"],
            response=parsed["response"],
            decision_type=parsed["decision_type"],
        )

        # If this decision ends the game, close the session log.
        if parsed["decision_type"] == "GRANT_EXIT":
            logger.end_session(session_id, outcome="ESCAPE")
        elif parsed["decision_type"] == "DENY_FINAL":
            logger.end_session(session_id, outcome="LOCKED")

        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": f"Gatekeeper turn failed: {e}"}), 500


@app.route("/api/logs/<session_id>", methods=["GET"])
def get_log(session_id):
    """
    Return a full session log as JSON (spec §15). Not used by the game itself;
    handy for debugging and for the evaluation tooling to fetch a run without
    touching the filesystem directly.
    """
    session = logger.get_session(session_id)
    if session is None:
        return jsonify({"error": f"No log for session: {session_id}"}), 404
    return jsonify(session)


if __name__ == "__main__":
    # debug=True auto-reloads when you save changes — handy in development.
    print(f"Starting Gatekeeper backend — active model: {config.ACTIVE_MODEL}")
    app.run(host="127.0.0.1", port=5000, debug=True)