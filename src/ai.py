"""Unified LLM client with a multi-model fallback chain via OpenRouter.

`complete()` tries each model in config.OPENROUTER_MODELS in order and returns
the first successful response. If a model is rate-limited, down, or returns an
error/empty body, it moves on to the next — so a brief never fails just because
one free model is unavailable.
"""
import requests

from . import config

_URL = "https://openrouter.ai/api/v1/chat/completions"
_HEADERS = {
    # OpenRouter asks for these for free-tier attribution; harmless if unset.
    "HTTP-Referer": "https://github.com/hack-parthsharma/telegram-market-bot",
    "X-Title": "Telegram Market Bot",
}


def _call_model(model, system, user, timeout, temperature):
    headers = dict(_HEADERS)
    headers["Authorization"] = f"Bearer {config.OPENROUTER_API_KEY}"
    body = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    r = requests.post(_URL, headers=headers, json=body, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(str(data["error"])[:200])
    content = data["choices"][0]["message"]["content"]
    if not content or not content.strip():
        raise ValueError("empty content")
    return content.strip()


def complete(system, user, temperature=0.4, timeout=60):
    """Return text from the first working model. Raises if the key is missing
    or every model in the chain fails (callers should try/except and degrade)."""
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    errors = []
    for model in config.OPENROUTER_MODELS:
        try:
            return _call_model(model, system, user, timeout, temperature)
        except Exception as exc:  # try the next model in the chain
            errors.append(f"{model}: {type(exc).__name__}")
    raise RuntimeError("all models failed -> " + " | ".join(errors))


def complete_meta(system, user, temperature=0.4, timeout=60):
    """Like complete() but also returns which model answered, for logging."""
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    errors = []
    for model in config.OPENROUTER_MODELS:
        try:
            return _call_model(model, system, user, timeout, temperature), model
        except Exception as exc:
            errors.append(f"{model}: {type(exc).__name__}")
    raise RuntimeError("all models failed -> " + " | ".join(errors))
