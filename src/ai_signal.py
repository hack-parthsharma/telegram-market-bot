"""AI-driven BUY / SELL / AVOID signal, grounded on computed indicators.

The LLM never sees raw price arrays — only the indicator snapshot dict — so its
call is cheap and its numbers are grounded. It returns strict JSON.
"""
import json
import requests

from . import config

SYSTEM = (
    "You are a disciplined technical analyst for Indian equities (NSE/BSE). "
    "Given a snapshot of technical indicators for one symbol on one timeframe, "
    "decide a single action: BUY, SELL, or AVOID. "
    "AVOID means unclear/choppy/no edge. Be conservative; prefer AVOID when signals conflict. "
    "This is not investment advice; it is a technical read. "
    "Respond with ONLY a JSON object, no markdown fences, with keys: "
    "signal (BUY|SELL|AVOID), confidence (0-100 int), entry (string or null), "
    "stop_loss (string or null), target (string or null), "
    "reasoning (<=60 words, plain English)."
)

_TEMPLATE = (
    "Symbol: {symbol}\nTimeframe: {timeframe}\nIndicator snapshot (JSON):\n{snap}\n\n"
    "Return the JSON decision now."
)


def _prompt(symbol, timeframe, snap):
    return _TEMPLATE.format(symbol=symbol, timeframe=timeframe,
                            snap=json.dumps(snap, indent=2))


def _parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON in model output: {text[:200]}")
    data = json.loads(text[start:end + 1])
    sig = str(data.get("signal", "AVOID")).upper()
    if sig not in ("BUY", "SELL", "AVOID"):
        sig = "AVOID"
    data["signal"] = sig
    return data


def _call_gemini(prompt):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
    }
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    body = {
        "model": config.GROQ_MODEL,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
    }
    r = requests.post(url, headers=headers, json=body, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def get_signal(symbol, timeframe, snap):
    prompt = _prompt(symbol, timeframe, snap)
    try:
        if config.AI_PROVIDER == "groq":
            raw = _call_groq(prompt)
        else:
            raw = _call_gemini(prompt)
        return _parse(raw)
    except Exception as exc:  # never let one symbol break the whole digest
        return {
            "signal": "AVOID",
            "confidence": 0,
            "entry": None, "stop_loss": None, "target": None,
            "reasoning": f"AI signal unavailable ({type(exc).__name__}). "
                         f"RSI {snap.get('rsi')}, price {snap.get('price_vs_ema20')} EMA20.",
        }
