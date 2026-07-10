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

# AI provider. "gemini" (default) or "groq". Only the chosen provider's key is required.
AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip()


def load_watchlist():
    with open(os.path.join(ROOT, "watchlist.yml"), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
