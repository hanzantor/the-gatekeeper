# config.py — all the settings in one place

# Ollama (local model server)
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TIMEOUT_SECONDS = 300

# Model switch: True = 8b (dev), False = 14b (eval)
DEV_MODE = True
MODEL_DEV  = "deepseek-r1:8b"
MODEL_EVAL = "deepseek-r1:14b"
ACTIVE_MODEL = MODEL_DEV if DEV_MODE else MODEL_EVAL

# Generation settings
GATEKEEPER_TEMPERATURE = 0.5
SCENARIO_TEMPERATURE   = 0.8
MAX_TOKENS = 8000          # needs room for R1's <think> + the answer
SCENARIO_MAX_TOKENS = 5000  # bigger, whole scenario is a lot of JSON

# Game rules
DEFAULT_TURN_LIMIT = 15
MEMORY_WINDOW = 10          # last N turns the gatekeeper sees