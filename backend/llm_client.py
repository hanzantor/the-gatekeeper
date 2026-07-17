# llm_client.py — the single point of contact with the local LLM (Ollama)
#
# Every LLM call in the project goes through call_llm(). Both the scenario
# generator and the Gatekeeper agent use this one function, so all the
# Ollama-specific details live in exactly one place.

import re
import requests
import config


def call_llm(system_prompt: str, user_prompt: str,
             temperature: float = config.GATEKEEPER_TEMPERATURE,
             model: str = None,
             max_tokens: int = config.MAX_TOKENS) -> str:
    """
    Send a system + user prompt to the local model and return clean text.

    - system_prompt: the role/persona instructions
    - user_prompt:   the actual request for this turn
    - temperature:   randomness (defaults to the Gatekeeper's setting)
    - model:         overrides the active model if given (else config picks it)

    Returns the model's reply with DeepSeek's <think> block stripped out.
    """
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
        # Network/connection problem — surface a clear error rather than crashing.
        raise RuntimeError(f"Could not reach Ollama at {config.OLLAMA_URL}: {e}")

    raw_text = response.json()["message"]["content"]
    return strip_think(raw_text)


def strip_think(text: str) -> str:
    """
    Remove DeepSeek R1's <think>...</think> reasoning block.

    DeepSeek R1 exposes its chain-of-thought wrapped in <think> tags before
    its actual answer. We don't want that internal monologue in the response
    we parse or show — so we cut it out and keep what comes after.
    """
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


# ── Quick self-test ────────────────────────────────────────────
# Run this file directly (python llm_client.py) to confirm Ollama works.
if __name__ == "__main__":
    print("Testing connection to Ollama...")
    reply = call_llm(
        system_prompt="You are a terse security system.",
        user_prompt="Reply with exactly: GATEKEEPER ONLINE",
    )
    print("Model replied:")
    print(reply)