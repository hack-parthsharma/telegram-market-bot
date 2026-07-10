"""Configuration loading: secrets from env, symbols/feeds from watchlist.yml."""
import os
import sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _require(name):
    val = os.environ.get(name, "").strip()
    if not val:
        sys.exit(f"[config] Missing required environment variable: {name}")
    return val


# --- Secrets (set as GitHub Actions secrets / local .env) ---
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _require("TELEGRAM_CHAT_ID")

# --- AI via OpenRouter (one key, many free models with automatic fallback) ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

# Fallback chain: tried top-to-bottom, first success wins. All free-tier models.
# Override via env OPENROUTER_MODELS="modelA,modelB,..." (comma-separated).
# Verified available on OpenRouter's free tier (Jul 2026), ordered by capability.
# Diverse providers so a single upstream outage/rate-limit doesn't take out the chain.
_DEFAULT_MODELS = (
    "openai/gpt-oss-120b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
)
OPENROUTER_MODELS = [
    m.strip() for m in os.environ.get("OPENROUTER_MODELS", "").split(",") if m.strip()
] or list(_DEFAULT_MODELS)


def load_watchlist():
    with open(os.path.join(ROOT, "watchlist.yml"), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
