# llm_client.py — the only point of contact with Ollama.
# Both the scenario generator and the Gatekeeper call through here.

import re
import requests
import config


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = config.GATEKEEPER_TEMPERATURE,
    model: str = None,
    max_tokens: int = config.MAX_TOKENS,
) -> str:

    if model is None:
        model = config.ACTIVE_MODEL

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],

        "stream": False,

        # Both scenario generation and Gatekeeper output are JSON.
        "format": "json",

        # IMPORTANT:
        # Disable DeepSeek R1's separate hidden thinking process.
        # The project evaluates the explicit "reasoning" JSON field instead.
        "think": False,

        "options": {
            "temperature": temperature,

            # Maximum generated response length.
            "num_predict": max_tokens,

            # Total context available for prompt + history + output.
            "num_ctx": 16384,
        },
    }

    try:
        response = requests.post(
            config.OLLAMA_URL,
            json=payload,
            timeout=config.OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Could not reach Ollama at {config.OLLAMA_URL}: {e}"
        )

    data = response.json()
    message = data.get("message", {})

    raw_text = message.get("content", "") or ""

    # Diagnostic information WITHOUT exposing the thinking text itself.
    print("\n===== OLLAMA RESULT =====")
    print("model:", data.get("model"))
    print("done_reason:", data.get("done_reason"))
    print("prompt tokens:", data.get("prompt_eval_count"))
    print("generated tokens:", data.get("eval_count"))
    print("content length:", len(raw_text))
    print("thinking length:", len(message.get("thinking", "") or ""))
    print("=========================\n")

    # Do not silently convert an empty model response into
    # REQUEST_EVIDENCE. Treat it as a technical failure.
    if not raw_text.strip():
        raise RuntimeError(
            "Ollama returned empty message.content. "
            f"done_reason={data.get('done_reason')}, "
            f"prompt_tokens={data.get('prompt_eval_count')}, "
            f"generated_tokens={data.get('eval_count')}, "
            f"thinking_length={len(message.get('thinking', '') or '')}"
        )

    return strip_think(raw_text)


def strip_think(text: str) -> str:
    """
    Defensive fallback for older/model-specific R1 output.
    Native thinking is disabled in the API request, so normally
    there should be no <think> block at all.
    """
    if not text:
        return ""

    # Remove complete think blocks.
    cleaned = re.sub(
        r"<think\b[^>]*>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Remove an unfinished think block if one somehow appears.
    cleaned = re.sub(
        r"<think\b[^>]*>.*$",
        "",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return cleaned.strip()