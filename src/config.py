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
_DEFAULT_MODELS = (
    "deepseek/deepseek-chat-v3-0324:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen-2.5-72b-instruct:free",
)
OPENROUTER_MODELS = [
    m.strip() for m in os.environ.get("OPENROUTER_MODELS", "").split(",") if m.strip()
] or list(_DEFAULT_MODELS)


def load_watchlist():
    with open(os.path.join(ROOT, "watchlist.yml"), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
