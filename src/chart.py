"""Render a candlestick chart (candles + EMAs + volume + RSI) to a PNG buffer."""
import io
import matplotlib
matplotlib.use("Agg")  # headless (GitHub Actions has no display)
import mplfinance as mpf


def render_chart(df_enriched, symbol, timeframe, signal=None):
    """df_enriched must contain EMA20/EMA50/EMA200 and RSI columns."""
    df = df_enriched.tail(120).copy()  # keep charts readable

    addplots = [
        mpf.make_addplot(df["EMA20"], color="#2962ff", width=1.0),
        mpf.make_addplot(df["EMA50"], color="#ff9800", width=1.0),
        mpf.make_addplot(df["RSI"], panel=2, color="#7e57c2", width=1.0, ylabel="RSI"),
    ]
    if df["EMA200"].notna().sum() > 0:
        addplots.append(mpf.make_addplot(df["EMA200"], color="#e91e63", width=1.0))

    style = mpf.make_mpf_style(base_mpf_style="yahoo", gridstyle=":", facecolor="white")
    title = f"{symbol}  [{timeframe}]"
    if signal:
        title += f"   ->  {signal}"

    buf = io.BytesIO()
    mpf.plot(
        df, type="candle", style=style, addplot=addplots,
        volume=True, panel_ratios=(6, 2, 2), figratio=(16, 10), figscale=1.2,
        title=title, tight_layout=True, savefig=dict(fname=buf, dpi=130, format="png"),
    )
    buf.seek(0)
    return buf
