"""Digest jobs: market summaries, Nifty 50 breadth, AI insight, and (on-demand)
per-symbol AI analysis with charts."""
import html
import json

from . import config, data, indicators, chart, ai_signal, ai, telegram

_EMOJI = {"BUY": "🟢", "SELL": "🔴", "AVOID": "⚪"}


def _fmt_pct(pct):
    arrow = "🔺" if pct > 0 else ("🔻" if pct < 0 else "▪️")
    return f"{arrow} {pct:+.2f}%"


def _quotes_for(entries):
    return data.batch_quotes([e["symbol"] for e in entries])


def _summary_block(title, entries, quotes):
    lines = [f"<b>{title}</b>"]
    for item in entries:
        q = quotes.get(item["symbol"])
        if not q:
            lines.append(f"• {html.escape(item['name'])}: n/a")
            continue
        lines.append(f"• {html.escape(item['name'])}: "
                     f"{q['last']:,.2f}  {_fmt_pct(q['pct'])}")
    return "\n".join(lines)


def _payload(entries, quotes):
    """Compact list of {name, last, pct} for feeding the LLM (only what resolved)."""
    out = []
    for e in entries:
        q = quotes.get(e["symbol"])
        if q:
            out.append({"name": e["name"], "last": round(q["last"], 2),
                        "pct": round(q["pct"], 2)})
    return out


# --------------------------------------------------------------------------
#  AI insight
# --------------------------------------------------------------------------
_PRE_SYSTEM = (
    "You are a sharp, concise Indian equity markets analyst. Using ONLY the data "
    "provided (overnight global indices, commodities, FX, and India's previous "
    "close), write a pre-market note for an Indian trader. "
    "Output PLAIN TEXT ONLY — no markdown, no HTML, no asterisks or hashes. "
    "Line 1: 'Bias: Positive/Neutral/Cautious — <one short reason>'. "
    "Then 4-6 lines each starting with '- ' covering: US & Asian cues, crude/USDINR/gold, "
    "India VIX if present, likely sector focus, and 1-2 things to watch at the open. "
    "Be specific with the numbers given. Under 140 words. End with 'Not investment advice.'"
)

_POST_SYSTEM = (
    "You are a sharp, concise Indian equity markets analyst. Using ONLY the data "
    "provided (index closes with % change, market breadth advances/declines, and the "
    "top gainers and losers), write a post-close market wrap for an Indian trader. "
    "Output PLAIN TEXT ONLY — no markdown, no HTML, no asterisks or hashes. "
    "Line 1: one-sentence summary of the session (direction + tone). "
    "Then 4-6 lines each starting with '- ' covering: breadth read, sector leaders vs "
    "laggards inferred from the movers, 2-3 notable stocks with their moves, and a brief "
    "setup/cue for tomorrow. Be specific with the numbers given. Under 150 words. "
    "End with 'Not investment advice.'"
)


def _send_ai_insight(label, emoji, system, payload):
    """Generate and send an AI insight message. Degrades silently on failure so
    the data-only brief is never blocked."""
    try:
        text, model = ai.complete_meta(system, json.dumps(payload, ensure_ascii=False))
    except Exception as exc:
        telegram.send_message(
            f"🤖 <b>AI {label}</b>\n<i>(insight unavailable: "
            f"{html.escape(type(exc).__name__)})</i>")
        return
    tag = model.split("/")[-1].replace(":free", "")
    # Plain text (parse_mode=None) so raw model output can't break Telegram parsing.
    telegram.send_message(f"{emoji} AI {label}\n\n{text}\n\n— via {tag}",
                          parse_mode=None)


# --------------------------------------------------------------------------
#  Breadth (all Nifty 50)
# --------------------------------------------------------------------------
def _monitor_report(entries):
    """Send breadth report and return {'rows', 'adv', 'dec', 'unch'} for the AI."""
    if not entries:
        return None
    quotes = data.batch_quotes([e["symbol"] for e in entries])
    rows = []
    for e in entries:
        q = quotes.get(e["symbol"])
        if not q:
            continue
        name = e.get("name") or e["symbol"].replace(".NS", "").replace(".BO", "")
        rows.append((name, q["last"], q["pct"]))
    if not rows:
        telegram.send_message("📋 <b>Nifty 50 Monitor</b>\nNo data available right now.")
        return None

    rows.sort(key=lambda r: r[2], reverse=True)
    adv = sum(1 for r in rows if r[2] > 0)
    dec = sum(1 for r in rows if r[2] < 0)
    unch = len(rows) - adv - dec

    def line(r):
        return f"{r[0]:<15}{r[1]:>10,.1f}  {r[2]:>+6.2f}%"

    head = [f"📋 <b>Nifty 50 Monitor</b>  ({len(rows)} stocks)",
            f"🟢 {adv} advances   🔴 {dec} declines   ⚪ {unch} flat", ""]
    top = ["<b>Top Gainers</b>", "<pre>"] + [line(r) for r in rows[:10]] + ["</pre>"]
    bot = ["<b>Top Losers</b>", "<pre>"] + [line(r) for r in rows[-10:][::-1]] + ["</pre>"]
    telegram.send_message("\n".join(head + top + [""] + bot))

    full = ["📄 <b>Nifty 50 — full movers (high → low)</b>", "<pre>"]
    full += [line(r) for r in rows] + ["</pre>"]
    telegram.send_message("\n".join(full))

    return {"rows": rows, "adv": adv, "dec": dec, "unch": unch}


# --------------------------------------------------------------------------
#  On-demand deep analysis (used by interactive mode / `run.py test`)
# --------------------------------------------------------------------------
def _analyze_symbol(symbol, timeframe="daily"):
    df, tf = data.fetch_ohlc(symbol, timeframe)
    snap, enriched = indicators.snapshot(df)
    decision = ai_signal.get_signal(symbol, tf, snap)
    sig = decision["signal"]

    caption_lines = [
        f"{_EMOJI.get(sig, '⚪')} <b>{html.escape(symbol)}</b>  [{tf}]  →  <b>{sig}</b>"
        + (f"  ({decision.get('confidence', 0)}%)" if decision.get("confidence") else ""),
        f"Price: {snap['close']:,.2f}  ({snap['change_pct']:+.2f}%)   RSI: {snap['rsi']}",
    ]
    lvl = []
    if decision.get("entry"):     lvl.append(f"Entry {html.escape(str(decision['entry']))}")
    if decision.get("stop_loss"): lvl.append(f"SL {html.escape(str(decision['stop_loss']))}")
    if decision.get("target"):    lvl.append(f"Target {html.escape(str(decision['target']))}")
    if lvl:
        caption_lines.append(" | ".join(lvl))
    caption_lines.append(f"S/R: {snap['support']:,.2f} / {snap['resistance']:,.2f}")
    if decision.get("reasoning"):
        caption_lines.append(f"\n💡 {html.escape(decision['reasoning'])}")

    img = chart.render_chart(enriched, symbol, tf, signal=sig)
    telegram.send_photo(img, caption="\n".join(caption_lines))


# --------------------------------------------------------------------------
#  Scheduled jobs
# --------------------------------------------------------------------------
def post_close():
    cfg = config.load_watchlist()
    indices = cfg.get("indices", [])
    idx_q = _quotes_for(indices)
    telegram.send_message(
        "📊 <b>Post-Close Market Digest</b>\n\n"
        + _summary_block("Indices", indices, idx_q))

    breadth = _monitor_report(cfg.get("monitor", []))

    payload = {
        "indices": _payload(indices, idx_q),
        "breadth": ({"advances": breadth["adv"], "declines": breadth["dec"],
                     "flat": breadth["unch"]} if breadth else {}),
        "top_gainers": ([{"name": r[0], "pct": round(r[2], 2)} for r in breadth["rows"][:10]]
                        if breadth else []),
        "top_losers": ([{"name": r[0], "pct": round(r[2], 2)} for r in breadth["rows"][-10:][::-1]]
                       if breadth else []),
    }
    _send_ai_insight("Market Wrap", "🤖", _POST_SYSTEM, payload)


def pre_market():
    cfg = config.load_watchlist()
    glob = cfg.get("global_markets", [])
    indices = cfg.get("indices", [])
    glob_q = _quotes_for(glob)
    idx_q = _quotes_for(indices)

    msg = ["🌅 <b>Pre-Market Brief</b>", "",
           _summary_block("Overnight / Global", glob, glob_q), "",
           _summary_block("India (prev close)", indices, idx_q)]
    telegram.send_message("\n".join(msg))

    payload = {"overnight_global": _payload(glob, glob_q),
               "india_prev_close": _payload(indices, idx_q)}
    _send_ai_insight("Pre-Market Insight", "🌅", _PRE_SYSTEM, payload)
