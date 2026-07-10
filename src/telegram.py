"""Minimal Telegram Bot API client (send text + photo)."""
import requests

from . import config

_BASE = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def send_message(text, parse_mode="HTML", disable_preview=True):
    r = requests.post(
        f"{_BASE}/sendMessage",
        data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text[:4096],
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def send_photo(photo_buffer, caption="", parse_mode="HTML"):
    r = requests.post(
        f"{_BASE}/sendPhoto",
        data={"chat_id": config.TELEGRAM_CHAT_ID,
              "caption": caption[:1024], "parse_mode": parse_mode},
        files={"photo": ("chart.png", photo_buffer, "image/png")},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()
