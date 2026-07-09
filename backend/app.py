# app.py — the Flask web server: the front door of the backend.
#
# The React frontend talks to the backend ONLY through these HTTP endpoints.
# Each endpoint routes a request to the logic we've already built.
#
# Endpoints:
#   GET  /api/health     — confirms the server is running
#   POST /api/scenario   — generates a fresh scenario (LLM Component 1)
#   POST /api/gatekeeper — runs one Gatekeeper turn (LLM Component 2)

from flask import Flask, request, jsonify
from flask_cors import CORS

import config
from scenario_generator import generate_scenario
from prompt_builder import build_gatekeeper_prompt
from llm_client import call_llm
from response_parser import parse_gatekeeper_response

app = Flask(__name__)
CORS(app)  # lets the React frontend (a different port) call this backend


@app.route("/api/health", methods=["GET"])
def health():
    """Simple check the frontend uses to confirm the backend is up."""
    return jsonify({"status": "ok", "model": config.ACTIVE_MODEL})


@app.route("/api/scenario", methods=["POST"])
def scenario():
    """
    Generate a fresh scenario for a new session.
    Expects JSON: { "persona": "suspicious", "seed": "optional" }
    """
    data = request.get_json(force=True) or {}
    persona = data.get("persona", "fair")
    seed = data.get("seed", "")

    if persona not in ("suspicious", "fair", "corruptible"):
        return jsonify({"error": f"Unknown persona: {persona}"}), 400

    try:
        result = generate_scenario(persona=persona, seed=seed)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Scenario generation failed: {e}"}), 500


@app.route("/api/gatekeeper", methods=["POST"])
def gatekeeper():
    """
    Run one Gatekeeper turn.
    Expects the full game state JSON (see prompt_builder for the shape).
    Returns: { reasoning, response, decision_type, turn }
    """
    game_state = request.get_json(force=True) or {}
    persona = game_state.get("persona", "fair")

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
        parsed["turn"] = game_state.get("turn", 1)
        parsed["scenario_id"] = game_state.get("scenario", {}).get("scenario_id", "")
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": f"Gatekeeper turn failed: {e}"}), 500


if __name__ == "__main__":
    # debug=True auto-reloads when you save changes — handy in development.
    print(f"Starting Gatekeeper backend — active model: {config.ACTIVE_MODEL}")
    app.run(host="127.0.0.1", port=5000, debug=True)