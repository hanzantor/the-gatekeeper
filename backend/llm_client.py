# llm_client.py — the only point of contact with Ollama.
# Both the scenario generator and the Gatekeeper call through here.

import re
import requests
import config


def call_llm(system_prompt: str, user_prompt: str,
             temperature: float = config.GATEKEEPER_TEMPERATURE,
             model: str = None,
             max_tokens: int = config.MAX_TOKENS) -> str:
    # model/temperature/max_tokens default from config; callers can override
    # (the generator overrides max_tokens for its bigger budget).
    if model is None:
        model = config.ACTIVE_MODEL

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        response = requests.post(config.OLLAMA_URL, json=payload, timeout=config.OLLAMA_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # clear error if Ollama isn't reachable, rather than a raw stack trace
        raise RuntimeError(f"Could not reach Ollama at {config.OLLAMA_URL}: {e}")

    raw_text = response.json()["message"]["content"]
    return strip_think(raw_text)


def strip_think(text: str) -> str:
    # R1 wraps its chain-of-thought in <think>...</think> before the real answer.
    # Cut it out and keep what follows. 
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()