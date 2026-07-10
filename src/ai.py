"""Unified LLM client with retry + multi-model fallback via OpenRouter.

Free (`:free`) endpoints are shared and frequently return transient HTTP 429
("rate-limited upstream", usually clears in ~1s). So we:
  1. retry each model a few times with short backoff on 429 / 5xx, then
  2. fall through to the next model in config.OPENROUTER_MODELS.
The first model that answers wins. A brief only loses its AI insight if EVERY
model fails every retry — in which case callers degrade gracefully.
"""
import time
import requests

from . import config

_URL = "https://openrouter.ai/api/v1/chat/completions"
_HEADERS = {
    "HTTP-Referer": "https://github.com/hack-parthsharma/telegram-market-bot",
    "X-Title": "Telegram Market Bot",
}
_RETRYABLE = {429, 500, 502, 503, 520, 524}
_ATTEMPTS_PER_MODEL = 3
_MAX_BACKOFF = 5.0


class _Retryable(Exception):
    def __init__(self, msg, wait=None):
        super().__init__(msg)
        self.wait = wait


def _once(model, system, user, timeout, temperature):
    headers = dict(_HEADERS, Authorization=f"Bearer {config.OPENROUTER_API_KEY}")
    body = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    r = requests.post(_URL, headers=headers, json=body, timeout=timeout)
    if r.status_code in _RETRYABLE:
        ra = r.headers.get("Retry-After")
        raise _Retryable(f"HTTP {r.status_code}", float(ra) if ra else None)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        code = err.get("code") if isinstance(err, dict) else None
        if code in _RETRYABLE:
            raise _Retryable(f"body error {code}")
        raise RuntimeError(str(err)[:200])
    content = data["choices"][0]["message"]["content"]
    if not content or not content.strip():
        raise ValueError("empty content")
    return content.strip()


def _call_model(model, system, user, timeout, temperature):
    last = None
    for i in range(_ATTEMPTS_PER_MODEL):
        try:
            return _once(model, system, user, timeout, temperature)
        except _Retryable as exc:
            last = exc
            if i < _ATTEMPTS_PER_MODEL - 1:
                wait = exc.wait if exc.wait is not None else 1.5 * (i + 1)
                time.sleep(min(wait, _MAX_BACKOFF))
    raise RuntimeError(f"retries exhausted ({last})")


def complete_meta(system, user, temperature=0.4, timeout=90):
    """Return (text, model_id) from the first working model; raise if all fail."""
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    errors = []
    for model in config.OPENROUTER_MODELS:
        try:
            return _call_model(model, system, user, timeout, temperature), model
        except Exception as exc:
            errors.append(f"{model.split('/')[-1]}: {type(exc).__name__}")
    raise RuntimeError("all models failed -> " + " | ".join(errors))


def complete(system, user, temperature=0.4, timeout=90):
    return complete_meta(system, user, temperature, timeout)[0]
