"""Digest jobs: market summaries + per-symbol AI analysis with charts."""
import html

from . import config, data, indicators, chart, ai_signal, telegram

_EMOJI = {"BUY": "🟢", "SELL": "🔴", "AVOID": "⚪"}


def _fmt_pct(pct):
    arrow = "🔺" if pct > 0 else ("🔻" if pct < 0 else "▪️")
    return f"{arrow} {pct:+.2f}%"


def _summary_block(title, entries):
    lines = [f"<b>{title}</b>"]
    for item in entries:
        snap = data.quote_snapshot(item["symbol"])
        if not snap:
            lines.append(f"• {html.escape(item['name'])}: n/a")
            continue
        lines.append(f"• {html.escape(item['name'])}: "
                     f"{snap['last']:,.2f}  {_fmt_pct(snap['pct'])}")
    return "\n".join(lines)


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
