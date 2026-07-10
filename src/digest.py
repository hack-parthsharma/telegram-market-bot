"""Digest jobs: market summaries + per-symbol AI analysis with charts."""
import html

from . import config, data, indicators, chart, ai_signal, telegram

_EMOJI = {"BUY": "🟢", "SELL": "🔴", "AVOID": "⚪"}


def _fmt_pct(pct):
    arrow = "🔺" if pct > 0 else ("🔻" if pct < 0 else "▪️")
    return f"{arrow} {pct:+.2f}%"


def _summary_block(title, entries):
    lines = [f"<b>{title}</b>"]
    quotes = data.batch_quotes([e["symbol"] for e in entries])
    for item in entries:
        q = quotes.get(item["symbol"])
        if not q:
            lines.append(f"• {html.escape(item['name'])}: n/a")
            continue
        lines.append(f"• {html.escape(item['name'])}: "
                     f"{q['last']:,.2f}  {_fmt_pct(q['pct'])}")
    return "\n".join(lines)


def _monitor_report(entries):
    """Compact breadth report for a large list (e.g. all Nifty 50): advances/
    declines, top gainers/losers, and a full sorted movers table. No charts/AI."""
    if not entries:
        return
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
        return

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

    # Full sorted table (fits well under Telegram's 4096-char limit for 50 rows).
    full = ["📄 <b>Nifty 50 — full movers (high → low)</b>", "<pre>"]
    full += [line(r) for r in rows] + ["</pre>"]
    telegram.send_message("\n".join(full))


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


def post_close():
    cfg = config.load_watchlist()
    header = ["📊 <b>Post-Close Market Digest</b>", ""]
    header.append(_summary_block("Indices", cfg.get("indices", [])))
    telegram.send_message("\n".join(header))

    # Tier 2: breadth over the full monitor list (all Nifty 50).
    _monitor_report(cfg.get("monitor", []))

    # Tier 1: deep AI analysis + chart for each curated watchlist symbol.
    for item in cfg.get("watchlist", []):
        try:
            _analyze_symbol(item["symbol"], item.get("timeframe", "daily"))
        except Exception as exc:
            telegram.send_message(
                f"⚠️ Could not analyze {html.escape(item['symbol'])}: "
                f"{html.escape(type(exc).__name__)}")


def pre_market():
    cfg = config.load_watchlist()
    lines = ["🌅 <b>Pre-Market Brief</b>", ""]
    lines.append(_summary_block("Overnight / Global", cfg.get("global_markets", [])))
    lines.append("")
    lines.append(_summary_block("India (prev close)", cfg.get("indices", [])))
    telegram.send_message("\n".join(lines))
