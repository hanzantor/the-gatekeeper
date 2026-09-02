// gatekeeperClient.js — all fetch() calls to the Flask backend.
//
// Kept deliberately thin: no state, no React, just "send this JSON, get
// that JSON back, throw a readable error if something went wrong." Every
// function returns a Promise<parsed JSON>; the caller (PersonaSelect,
// App.jsx's Scenario Loader, the dialogue panel) decides what to do with
// the result and how to show loading/error state.
//
// ASSUMPTION: Flask is running on localhost:5000 (its default). Change
// BASE_URL below if your backend binds to a different host/port.

const BASE_URL = 'http://localhost:5000';

// Ollama on an 8B/14B model, CPU-only, can genuinely take a long time to
// respond. DeepSeek R1 spends real generation time on its <think> block
// before the actual answer, so this is worse than it looks from the
// model size alone. Kept in step with config.OLLAMA_TIMEOUT_SECONDS on
// the backend (240s) — set slightly higher here so Flask's own timeout
// fires first with a specific error, rather than the browser cutting the
// request off first and masking what was actually happening.
const DEFAULT_TIMEOUT_MS = 300_000;

/**
 * Shared request helper. Throws a GatekeeperClientError with the response
 * status and body text on any non-2xx response, on a timeout, or on a
 * network failure, so callers can show a real message instead of a
 * silent failure or an indefinite spinner.
 */
async function request(path, { timeoutMs = DEFAULT_TIMEOUT_MS, ...options } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options,
    });
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new GatekeeperClientError(
        `${options.method ?? 'GET'} ${path} timed out after ${timeoutMs}ms — Ollama may still be generating a response.`,
        { cause: err }
      );
    }
    // fetch() itself threw — almost always means Flask isn't running,
    // or CORS is blocking the request.
    throw new GatekeeperClientError(
      `Could not reach the backend at ${BASE_URL}${path}. Is Flask running?`,
      { cause: err }
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new GatekeeperClientError(
      `${options.method ?? 'GET'} ${path} failed: ${response.status} ${response.statusText}${body ? ` — ${body}` : ''}`,
      { status: response.status, body }
    );
  }

  return response.json();
}

export class GatekeeperClientError extends Error {
  constructor(message, { status, body, cause } = {}) {
    super(message, { cause });
    this.name = 'GatekeeperClientError';
    this.status = status;
    this.body = body;
  }
}

/**
 * POST /api/scenario — starts a new session.
 * @param {string} persona  'suspicious' | 'fair' | 'corruptible'
 * @param {object} [opts]
 * @param {string} [opts.seed]     optional theme hint, per spec §15
 * @param {string} [opts.saveAs]   dev/eval only: freeze the generated scenario
 *                                  to fixtures/<name>.json for matched runs
 * @param {string} [opts.fixture]  dev/eval only: replay a frozen scenario by
 *                                  name instead of generating a fresh one
 * @returns {Promise<object>} full scenario JSON (spec §5)
 */
export function getScenario(persona, { seed = '', saveAs = '', fixture = '' } = {}) {
  return request('/api/scenario', {
    method: 'POST',
    body: JSON.stringify({ persona, seed, save_as: saveAs, fixture }),
  });
}

/**
 * POST /api/gatekeeper — main per-turn call. Send the full game state,
 * get back the Gatekeeper's reasoning/response/decision (spec §11, §13).
 * @param {object} gameState
 * @returns {Promise<object>} { response, reasoning, decision_type, turn, scenario_id }
 */
export function sendTurn(gameState) {
  return request('/api/gatekeeper', {
    method: 'POST',
    body: JSON.stringify(gameState),
  });
}

/**
 * POST /api/buttons — contextual dialogue options for the next turn
 * (spec §10).
 * @param {object} lightState  inventory + scenario + last gatekeeper response
 * @returns {Promise<{ buttons: Array<{ label: string, type: string }> }>}
 */
export function getButtons(lightState) {
  return request('/api/buttons', {
    method: 'POST',
    body: JSON.stringify(lightState),
  });
}

/**
 * GET /api/health — confirms the backend is up. Useful to call once on
 * app mount so a dead backend shows a clear message instead of every
 * later call failing mysteriously. Short timeout: this should be near-
 * instant if Flask is running at all — no reason to wait 2 minutes to
 * find out it isn't.
 * @returns {Promise<{ status: string }>}
 */
export function checkHealth() {
  return request('/api/health', { method: 'GET', timeoutMs: 5_000 });
}

/**
 * GET /api/logs/<session_id> — full session log as JSON (spec §15).
 * Not needed by the game itself; useful for debugging or the evaluation
 * tooling to fetch a specific run without touching the filesystem.
 * @param {string} sessionId
 * @returns {Promise<object>}
 */
export function getSessionLog(sessionId) {
  return request(`/api/logs/${encodeURIComponent(sessionId)}`, { method: 'GET' });
}