"""Market data via yfinance (free, no API key)."""
import yfinance as yf

# Map a requested timeframe -> (yfinance interval, history period).
# yfinance limits intraday history, so periods are chosen to stay within them.
TIMEFRAMES = {
    "5m":  ("5m", "5d"),
    "15m": ("15m", "10d"),
    "30m": ("30m", "20d"),
    "1h":  ("60m", "60d"),
    "daily": ("1d", "8mo"),
    "weekly": ("1wk", "3y"),
}


def normalize_timeframe(tf):
    if not tf:
        return "daily"
    tf = tf.strip().lower()
    aliases = {"5min": "5m", "15min": "15m", "30min": "30m",
               "1d": "daily", "day": "daily", "d": "daily",
               "1w": "weekly", "w": "weekly", "60m": "1h", "1hr": "1h"}
    tf = aliases.get(tf, tf)
    return tf if tf in TIMEFRAMES else "daily"


def fetch_ohlc(symbol, timeframe="daily"):
    """Return a cleaned OHLCV DataFrame for a symbol at the given timeframe."""
    tf = normalize_timeframe(timeframe)
    interval, period = TIMEFRAMES[tf]
    df = yf.download(
        symbol, period=period, interval=interval,
        auto_adjust=False, progress=False, threads=False,
    )
    if df is None or df.empty:
        raise ValueError(f"No data returned for {symbol} ({tf})")
    # yfinance may return a MultiIndex on columns for a single ticker.
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.title)  # Open/High/Low/Close/Volume
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    return df, tf


def batch_quotes(symbols):
    """Last close + % change for many symbols in ONE download (fast).

    Returns {symbol: {"last": float, "pct": float}}; symbols with no data
    are simply omitted.
    """
    symbols = list(dict.fromkeys(symbols))  # de-dupe, keep order
    if not symbols:
        return {}
    df = yf.download(symbols, period="7d", interval="1d", auto_adjust=False,
                     progress=False, threads=True, group_by="ticker")
    out = {}
    for sym in symbols:
        try:
            sub = df[sym] if len(symbols) > 1 else df
            closes = sub["Close"].dropna()
            if len(closes) < 2:
                continue
            last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
            out[sym] = {"last": last, "pct": (last - prev) / prev * 100 if prev else 0.0}
        except Exception:
            continue
    return out


def quote_snapshot(symbol):
    """Latest close and % change vs previous close (for summaries)."""
    df = yf.download(symbol, period="7d", interval="1d",
                     auto_adjust=False, progress=False, threads=False)
    if df is None or df.empty:
        return None
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    closes = df["Close"].dropna()
    if len(closes) < 2:
        return None
    last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
    pct = (last - prev) / prev * 100.0 if prev else 0.0
    return {"last": last, "prev": prev, "pct": pct}
