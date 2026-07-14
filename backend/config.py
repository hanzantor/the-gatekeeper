# config.py — central configuration for The Gatekeeper backend

# ── Ollama connection ──────────────────────────────────────────
# Where the local Ollama server listens. This is the default;
# you won't need to change it unless you move Ollama elsewhere.
OLLAMA_URL = "http://localhost:11434/api/chat"

# ── Ollama timeout ──────────────────────────────────────────────
# DeepSeek R1 spends real generation time on its <think> block before the
# actual answer — on CPU-only inference, that adds up fast. 120s was too
# tight for scenario generation specifically (structured JSON + fresh
# prose for 4-6 clues). Raise further if your machine still times out.
OLLAMA_TIMEOUT_SECONDS = 240

# ── Model selection ────────────────────────────────────────────
# The 8B/14B switch lives here. Change DEV_MODE to flip between them.
#   True  → development model (8b)  — fast, for building and testing
#   False → evaluation model (14b)  — slower, better reasoning, for Phase 8
DEV_MODE = True

MODEL_DEV  = "deepseek-r1:8b"
MODEL_EVAL = "deepseek-r1:14b"

# The active model, chosen automatically from DEV_MODE above.
ACTIVE_MODEL = MODEL_DEV if DEV_MODE else MODEL_EVAL

# ── Generation settings ────────────────────────────────────────
# Per-call-type settings. The Gatekeeper and the scenario generator
# can use different temperatures — the generator a touch higher for
# variety, the Gatekeeper a touch lower for consistent reasoning.
GATEKEEPER_TEMPERATURE = 0.7   # the agent's per-turn reasoning
SCENARIO_TEMPERATURE   = 0.8   # scenario generation — slightly more creative
MAX_TOKENS = 800               # cap on response length (num_predict in Ollama)

# ── Game rules ─────────────────────────────────────────────────
DEFAULT_TURN_LIMIT = 15        # turns before DENY_FINAL
MEMORY_WINDOW = 10             # how many past turns the agent sees each prompt