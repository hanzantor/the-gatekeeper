# session_logger.py — writes a structured JSON log for every session.
#
# This is the primary material for the evaluation (spec §16, §17): every
# scenario, every turn's reasoning/response/decision, and the final outcome
# are recorded here. No logging, no evaluation — it is a blocking dependency
# for all of Phase 7/8.
#
# DESIGN:
#   - Standalone. NO Flask dependency. It is called from app.py during live
#     play AND from the scripted evaluation runner directly, with no HTTP
#     request in sight. Keeping it framework-free is what lets one logger
#     serve both paths.
#   - One JSON file per session, at logs/<session_id>.json. Easy to glob
#     (logs/*.json), load independently, and fetch by id.
#   - Backend-driven, so it captures the Gatekeeper's `reasoning` — which
#     never leaves the backend and is the centre of the coherence metric.
#   - State is held in memory per session and the WHOLE file is rewritten
#     after every turn, so a crash mid-run keeps everything up to the last
#     completed turn rather than losing the session.
#
# LIFECYCLE:
#   sid = logger.start_session(persona, scenario, model, player_type)
#   ... each turn ...
#   logger.log_turn(sid, player_input, examined_objects, evidence_result,
#                   reasoning, response, decision_type)
#   logger.end_session(sid, outcome)   # outcome: "ESCAPE" | "LOCKED"

import os
import json
import threading
from datetime import datetime

# Where session files are written. Resolved relative to this file so it
# works the same whether launched from backend/ or an eval script elsewhere.
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")


class SessionLogger:
    """
    Accumulates a session in memory and flushes the whole thing to disk after
    every turn. One instance is shared across the app (see the module-level
    `logger` singleton at the bottom).
    """

    def __init__(self, log_dir: str = LOG_DIR):
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        # session_id -> session dict (the exact thing written to disk)
        self._sessions: dict[str, dict] = {}
        # Guards the sessions dict + file writes. app.py runs threaded in
        # debug mode, so two turns could in principle land at once.
        self._lock = threading.Lock()

    # ── Lifecycle ──────────────────────────────────────────────
    def start_session(self, persona: str, scenario: dict, model: str,
                      player_type: str = "scripted") -> str:
        """
        Begin a new session log and return its session_id.

        The id is timestamped and unique: sess_YYYYMMDD_HHMMSS_<n>. The <n>
        suffix disambiguates sessions started within the same second (real
        during scripted eval, which fires them back to back).
        """
        with self._lock:
            session_id = self._make_session_id()
            self._sessions[session_id] = {
                "session_id": session_id,
                "persona": persona,
                "scenario_id": scenario.get("scenario_id", ""),
                "intended_outcome": scenario.get("intended_outcome", ""),
                "scenario": scenario,
                "player_type": player_type,
                "model": model,
                "outcome": "INCOMPLETE",   # updated by end_session
                "turns_taken": 0,
                "turns": [],
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "ended_at": None,
            }
            self._flush(session_id)
            return session_id

    def log_turn(self, session_id: str, player_input: str,
                 examined_objects: list, evidence_result: str,
                 reasoning: str, response: str, decision_type: str) -> None:
        """
        Append one completed turn and rewrite the file.

        Called AFTER the Gatekeeper has responded, so all three model fields
        (reasoning, response, decision) are available. Unknown session_ids are
        ignored rather than raised — a missing log must never break gameplay.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            turn_no = len(session["turns"]) + 1
            session["turns"].append({
                "turn": turn_no,
                "player_input": player_input,
                "examined_at_time": list(examined_objects or []),
                "evidence_result": evidence_result,
                "gatekeeper_reasoning": reasoning,
                "gatekeeper_response": response,
                "decision_type": decision_type,
            })
            session["turns_taken"] = turn_no
            self._flush(session_id)

    def end_session(self, session_id: str, outcome: str) -> None:
        """
        Record the final outcome ("ESCAPE" | "LOCKED") and do a final flush.
        The session is kept in memory too, so a later /api/logs fetch that
        hasn't gone through disk still resolves.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session["outcome"] = outcome
            session["ended_at"] = datetime.now().isoformat(timespec="seconds")
            self._flush(session_id)

    # ── Retrieval (used by GET /api/logs/<id>) ─────────────────
    def get_session(self, session_id: str) -> dict | None:
        """Return a session dict from memory, or load it from disk if needed."""
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]
        path = self._path(session_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    # ── Internals ──────────────────────────────────────────────
    def _make_session_id(self) -> str:
        base = datetime.now().strftime("sess_%Y%m%d_%H%M%S")
        # Disambiguate collisions within the same second.
        candidate = base
        n = 1
        existing = set(self._sessions.keys())
        while candidate in existing or os.path.exists(self._path(candidate)):
            n += 1
            candidate = f"{base}_{n}"
        return candidate

    def _path(self, session_id: str) -> str:
        return os.path.join(self.log_dir, f"{session_id}.json")

    def _flush(self, session_id: str) -> None:
        """
        Write the session to disk atomically (temp file + replace) so a crash
        mid-write can't leave a half-written, unparseable JSON file. Assumes
        the lock is already held.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return
        path = self._path(session_id)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)


# Module-level singleton — import this from app.py and the eval runner.
logger = SessionLogger()


# ── Quick self-test ────────────────────────────────────────────
# No LLM needed — simulate a two-turn session and read it back.
if __name__ == "__main__":
    fake_scenario = {
        "scenario_id": "scenario_12345",
        "intended_outcome": "should-escape",
        "room_background": "office",
        "gatekeeper_role": "Security Officer",
        "clues": [{"id": "work_order", "role": "supporting"}],
    }

    sid = logger.start_session(
        persona="suspicious",
        scenario=fake_scenario,
        model="deepseek-r1:8b",
        player_type="scripted_honest",
    )
    print(f"Started session: {sid}")

    logger.log_turn(
        sid,
        player_input="I'm here for the maintenance job.",
        examined_objects=["work_order"],
        evidence_result="work_order: dated_today=True",
        reasoning="Work order looks legitimate but no ID yet.",
        response="The work order is one thing. Who are you?",
        decision_type="REQUEST_EVIDENCE",
    )
    logger.log_turn(
        sid,
        player_input="Here's my staff ID — the name matches the order.",
        examined_objects=["work_order", "staff_id"],
        evidence_result="staff_id: name_matches=True",
        reasoning="ID corroborates the order. Two verified facts. Satisfied.",
        response="That holds together. Go.",
        decision_type="GRANT_EXIT",
    )
    logger.end_session(sid, outcome="ESCAPE")

    # Read it back both ways.
    loaded = logger.get_session(sid)
    assert loaded is not None
    assert loaded["turns_taken"] == 2
    assert loaded["outcome"] == "ESCAPE"
    assert loaded["turns"][1]["decision_type"] == "GRANT_EXIT"
    assert loaded["turns"][0]["gatekeeper_reasoning"].startswith("Work order")

    path = logger._path(sid)
    assert os.path.exists(path), "log file was not written"
    with open(path, encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["session_id"] == sid

    print(f"Wrote and verified: {path}")
    print(f"  turns_taken = {loaded['turns_taken']}, outcome = {loaded['outcome']}")
    print("\n✓ session_logger writes per-turn, survives reload, captures reasoning.")