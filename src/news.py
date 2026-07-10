"""Pull India-market headlines from RSS feeds and push a filtered digest."""
import html
import feedparser

from . import config, telegram


def _matches(entry, keywords):
    if not keywords:
        return True
    hay = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(k.lower() in hay for k in keywords)


def run(max_items=12):
    cfg = config.load_watchlist()
    feeds = cfg.get("news_feeds", [])
    keywords = cfg.get("news_keywords", [])

    seen_titles = set()
    items = []
    for url in feeds:
        parsed = feedparser.parse(url)
        for e in parsed.entries:
            title = e.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            if _matches(e, keywords):
                seen_titles.add(title)
                items.append((title, e.get("link", "")))
            if len(items) >= max_items:
                break
        if len(items) >= max_items:
            break

    if not items:
        return

    lines = ["📰 <b>India Markets — News</b>", ""]
    for title, link in items:
        t = html.escape(title)
        lines.append(f"• <a href=\"{link}\">{t}</a>" if link else f"• {t}")
    telegram.send_message("\n".join(lines), disable_preview=True)


if __name__ == "__main__":
    run()
