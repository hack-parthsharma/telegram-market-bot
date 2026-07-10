"""Technical indicators computed with pandas (no external TA dependency)."""
import numpy as np
import pandas as pd


def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def macd(series, fast=12, slow=26, signal=9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line, macd_line - signal_line


def enrich(df):
    """Add indicator columns to an OHLCV frame."""
    out = df.copy()
    close = out["Close"]
    out["EMA20"] = ema(close, 20)
    out["EMA50"] = ema(close, 50)
    out["EMA200"] = ema(close, 200)
    out["RSI"] = rsi(close, 14)
    out["MACD"], out["MACD_SIGNAL"], out["MACD_HIST"] = macd(close)
    out["VOL_AVG20"] = out["Volume"].rolling(20).mean()
    return out


def support_resistance(df, lookback=40):
    window = df.tail(lookback)
    return {
        "support": float(window["Low"].min()),
        "resistance": float(window["High"].max()),
    }


def snapshot(df):
    """Compact dict of the latest indicator state — this is what the LLM sees."""
    d = enrich(df)
    last = d.iloc[-1]
    prev = d.iloc[-2] if len(d) > 1 else last
    sr = support_resistance(d)
    vol = float(last["Volume"])
    vol_avg = float(last["VOL_AVG20"]) if not pd.isna(last["VOL_AVG20"]) else vol

    def r(x, n=2):
        return round(float(x), n)

    return {
        "close": r(last["Close"]),
        "change_pct": r((last["Close"] - prev["Close"]) / prev["Close"] * 100 if prev["Close"] else 0),
        "ema20": r(last["EMA20"]),
        "ema50": r(last["EMA50"]),
        "ema200": r(last["EMA200"]),
        "rsi": r(last["RSI"], 1),
        "macd": r(last["MACD"], 3),
        "macd_signal": r(last["MACD_SIGNAL"], 3),
        "macd_hist": r(last["MACD_HIST"], 3),
        "volume": int(vol),
        "vol_vs_avg20_pct": r((vol / vol_avg - 1) * 100 if vol_avg else 0, 0),
        "support": r(sr["support"]),
        "resistance": r(sr["resistance"]),
        "price_vs_ema20": "above" if last["Close"] > last["EMA20"] else "below",
        "ema20_vs_ema50": "above" if last["EMA20"] > last["EMA50"] else "below",
    }, d
