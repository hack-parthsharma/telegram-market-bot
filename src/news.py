"""Pull India-market headlines from RSS and push only FRESH ones to Telegram.

"Fresh" = not sent in a previous run. Because GitHub Actions runners are
ephemeral, the set of already-sent article IDs is persisted to a small JSON
state file (cached between runs by the workflow).
"""
import os
import html
import json
import feedparser

from . import config, telegram

STATE_DIR = os.environ.get("NEWS_STATE_DIR", ".state")
STATE_FILE = os.path.join(STATE_DIR, "seen_news.json")

MAX_SEND = int(os.environ.get("NEWS_MAX_SEND", "25"))   # cap per run (flood guard)
MAX_REMEMBER = 1500                                     # cap stored IDs


def _entry_id(e):
    return (e.get("id") or e.get("link") or e.get("title") or "").strip()


def _matches(entry, keywords):
    if not keywords:
        return True
    hay = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(k.lower() in hay for k in keywords)


def _load_seen():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return list(data.get("ids", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_seen(ids):
    os.makedirs(STATE_DIR, exist_ok=True)
    ids = ids[-MAX_REMEMBER:]  # keep only the most recent
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump({"ids": ids}, fh)


def _send_batches(items):
    """Send fresh headlines, chunked under Telegram's 4096-char limit."""
    header = "📰 <b>India Markets — Fresh News</b>"
    chunk, size = [header], len(header)
    for title, link in items:
        t = html.escape(title)
        line = f"• <a href=\"{link}\">{t}</a>" if link else f"• {t}"
        if size + len(line) + 1 > 3900 and len(chunk) > 1:
            telegram.send_message("\n".join(chunk), disable_preview=True)
            chunk, size = [header], len(header)
        chunk.append(line)
        size += len(line) + 1
    if len(chunk) > 1:
        telegram.send_message("\n".join(chunk), disable_preview=True)


def run():
    cfg = config.load_watchlist()
    feeds = cfg.get("news_feeds", [])
    keywords = cfg.get("news_keywords", []) or []

    seen = _load_seen()
    seen_set = set(seen)
    first_run = not seen  # avoid dumping the entire backlog on the very first run

    fresh = []            # (title, link) to send
    fresh_ids = []        # ids to remember
    for url in feeds:
        parsed = feedparser.parse(url)
        for e in parsed.entries:
            eid = _entry_id(e)
            title = e.get("title", "").strip()
            if not eid or not title or eid in seen_set:
                continue
            seen_set.add(eid)          # remember it regardless
            fresh_ids.append(eid)
            if _matches(e, keywords):
                fresh.append((title, e.get("link", "")))

    # Persist everything we saw so we never resend it.
    _save_seen(seen + fresh_ids)

    if not fresh:
        return
    # On the first-ever run there is no history, so cap hard to avoid a flood.
    to_send = fresh[:MAX_SEND]
    if first_run:
        to_send = fresh[:min(MAX_SEND, 10)]
    _send_batches(to_send)


if __name__ == "__main__":
    run()
