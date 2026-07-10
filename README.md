# 📈 Telegram Market Bot (India) — 100% free

Automated, free stock-market automation for Indian markets (NSE/BSE), delivered to Telegram and run entirely on **GitHub Actions cron** — no server, no cost.

## What it does

| Job | When (IST) | Content |
|-----|-----------|---------|
| **Pre-Market Brief** | 08:45 Mon–Fri | Overnight global indices + India prev close |
| **Post-Close Digest** | 15:45 Mon–Fri | Index summary + per-symbol **AI analysis**: candlestick chart (EMA/RSI/volume) with a **BUY / SELL / AVOID** signal, entry/SL/target, and reasoning |
| **Market News** | 09:00 & 16:30 Mon–Fri | Filtered India-market headlines from RSS |

- **Data:** `yfinance` (free, no key) — daily & intraday NSE/BSE
- **Signals:** AI-driven (Google Gemini free tier; Groq swap-in), *grounded* on locally-computed indicators so numbers are real
- **Charts:** `mplfinance` candlesticks sent as photos
- **Cost:** ₹0 — GitHub Actions free minutes + free API tiers

> ⚠️ Educational/technical analysis only — **not investment advice**.

---

## Setup (about 10 minutes)

### 1. Create your Telegram bot
1. In Telegram, message **@BotFather** → `/newbot` → follow prompts → copy the **bot token**.
2. Send any message to your new bot (so it can message you back).
3. Get your **chat id**: open in a browser
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   and copy the `"chat":{"id": ...}` number.

### 2. Get a free AI key
- **Gemini (default):** https://aistudio.google.com/apikey → create key.
- *or* **Groq:** https://console.groq.com/keys → create key, and set variable `AI_PROVIDER=groq`.

### 3. Push this repo to GitHub
```bash
git init && git add . && git commit -m "init"
git branch -M main
git remote add origin https://github.com/<you>/telegram-market-bot.git
git push -u origin main
```

### 4. Add secrets in GitHub
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|--------|-------|
| `TELEGRAM_BOT_TOKEN` | from BotFather |
| `TELEGRAM_CHAT_ID` | your chat id |
| `GEMINI_API_KEY` | from AI Studio (or `GROQ_API_KEY`) |

Optional **Variables** (not secrets): `AI_PROVIDER`, `GEMINI_MODEL`, `GROQ_MODEL`.

### 5. Test it
Repo → **Actions → Post-Close Digest → Run workflow**. You should get a chart + signal in Telegram within ~1–2 min. The crons then run automatically on schedule.

---

## Customize
- **Symbols / feeds:** edit `watchlist.yml` (use Yahoo tickers, e.g. `RELIANCE.NS`, `TCS.NS`).
- **Per-symbol timeframe:** add `timeframe: 5m` under a watchlist entry (options: `5m,15m,30m,1h,daily,weekly`).
- **Schedules:** edit the `cron:` lines in `.github/workflows/*.yml` (times are **UTC**; IST = UTC + 5:30).

## Run locally (optional)
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in values, then load them into your shell
python run.py test RELIANCE.NS daily   # one-off analysis
python run.py postclose                # full digest
```

## Notes & limits
- GitHub cron can be delayed a few minutes at peak times — fine for digests.
- `yfinance` is an unofficial Yahoo feed; occasional gaps are handled per-symbol (one failure won't break the digest).
- Free AI tiers have rate limits; the watchlist is small by design. If the AI call fails, the bot still sends the chart with an indicator-only note.
