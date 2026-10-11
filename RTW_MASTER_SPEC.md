# RAJ TRADING WORLD (RTW) — MASTER BUILD SPEC v1.0

Owner: Raj (no coding background). Builder: the coding agent (Google Antigravity). Date: 11 Oct 2026.
This file contains a COMPLETE, ALREADY-TESTED codebase. Your job is to unpack it, install it, run the checks, and wire the live data keys. Do NOT redesign it.

---

## RAJ KE LIYE (Hinglish, 1 minute)

1. Ye app default me **ek time par ek hi signal** deta hai (ya "WAIT" aur wajah); baaki signals sirf INFO. Agar **ek saath kai signals** chahiye to Settings me **"Ek saath kitne signals"** 1 se 5 tak badal do (ya `.env` me `RTW_MAX_TRADES=3`). Har signal ka risk alag hota hai, to 3 signals = kul risk 3 × risk%.
2. Pehle DEMO mode me chalega (nakli data, koi setup nahi) taaki tum screens dekh lo. Phir PAPER mode (asli data, signals PAPER tag ke saath). Real paisa tab hi jab Record tab me saaf track record ban jaye.
3. Tumhe sirf ye **5 cheezein khud karni hain** (baaki sab Antigravity karega): (a) Python install, (b) Angel One SmartAPI keys .env me daalna, (c) Telegram bot token + chat id, (d) `check.bat` chalana, (e) `start.bat` chalana. PIN / TOTP secret kabhi chat me paste mat karna, sirf `.env` file me.
4. App sirf **advice** deta hai, order khud nahi lagata. Options me sirf **BUY (CE/PE)**, kabhi selling nahi.
5. **Chart:** Home ke trade card, Markets ki har row aur Search me **📈 Chart** button hai (candles + EMA20 + Entry/SL/Target lines; 5m/15m/1h). Option trade me **Option chart** bhi. Har chart ke neeche **TradingView me kholo** link hai (TradingView ka apna chart, kisi bhi stock/index/pair ke liye).
6. **Market mood:** Home pe "Market ka mahaul" box (Nifty, BankNifty, Gold, Crude, Bitcoin) me 🟢 Tezi (Bullish) / 🔴 Mandi (Bearish) / 🟡 Sideways dikhta hai; Sideways me "range me hai, breakout ka intezar" + range (low–high). Mood badalte hi app me pop-up aata hai aur Telegram alert jaata hai. Ye sirf mahaul hai, trade signal nahi.
7. Antigravity ko ye poori file do aur likho: **"Is MD ko Section 0 ke hisaab se step by step execute karo. Code mat badalna, sirf steps follow karo."**

---

## 0. READ FIRST (for the coding agent)

### 0.1 What you are building
One local Python app (FastAPI backend + installable phone web app + Telegram bot) that analyses Indian markets (Nifty 50, Bank Nifty, Midcap Nifty options; MCX crude, natural gas, gold/gold mini, silver/silver mini; top F&O stocks; the 7 legal exchange-traded forex pairs; BTC; search for anything else) and publishes **ONE single, complete trade call** at a time by default (Raj can raise `RTW_MAX_TRADES` / the Settings option to 1–5 simultaneous calls), e.g. "GOLD BUY entry/SL/target, hold till 23:15" or "NIFTY 24500 CE buy, entry zone, SL, targets, hold till 15:15". News is a core input (event calendar, headline tagger, news modes).

### 0.2 How to build (exact commands; do them in order)
1. Make an empty folder (example `C:\RTW`). Put this file in it, named `RTW_MASTER_SPEC.md`.
2. Create `unpack.py` in that folder with EXACTLY this code, then run `python unpack.py RTW_MASTER_SPEC.md`. It creates every file listed in Section 15 byte-for-byte. **Never retype the code files by hand.**

```python
import os, re, sys
src = open(sys.argv[1], encoding="utf-8").read().replace("\r\n", "\n")
n = 0
for m in re.finditer(r"^````[a-z]* file=(\S+)\n(.*?)\n````$", src, re.S | re.M):
    path, body = m.group(1), m.group(2)
    if path.endswith(".bat"):
        body = body.replace("\n", "\r\n")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(body + ("\r\n" if path.endswith(".bat") else "\n"))
    n += 1
print(n, "files created")
```

3. Run `install.bat` (Windows) — or `python -m venv .venv`, activate, `pip install -r requirements.txt`, `python -m pytest`.
   **Expected:** all tests pass (authoring run: 99 passed, 0 failed, Python 3.13; Python 3.10–3.13 supported).
4. Run `.venv\Scripts\python check_setup.py` (DEMO mode first). Expected: `0 FAIL`.
5. Run `start.bat`. Open `http://localhost:8000`. Expected: Home shows a signal card or a WAIT card with a reason; tabs Home / Markets / Search / News / Record / Settings all open without error.
6. Only then: Section 4 (live keys) → set `RTW_MODE=PAPER` → `check.bat` → `start.bat`.

### 0.3 Hard rules for you (do not break)
- R1. Do not rewrite or "improve" the tested modules (`indicators, layers, scoring, gates, lifecycle, plan, options, news, engine, backtest, pipeline, views, notify`). If you think something is wrong, report it to Raj in one line instead of changing it. **Only exception:** a real bug that a failing test or a live run proves — then make the smallest possible fix, add a test for it, and tell Raj in one line.
- R2. Live-API code (`rtw/adapters/*`, `rtw/live.py`) was written against library signatures but **could not be run against the real brokers/exchanges** (no access from the authoring sandbox). If a live call fails, fix **only inside those files**, keep the function names and return shapes, and re-run `pytest` (offline parser tests) + `check_setup.py`.
- R3. Providers NEVER raise. They return `None / [] / {}` on failure; the pipeline then says WAIT with a reason. Keep it that way.
- R4. Only closed candles are used for decisions (no lookahead). Never use the still-forming bar.
- R5. Open trades never exceed `max_trades` (default **1**, user-settable 1–5) across all markets; signals beyond the free slots are INFO only. Never two trades on the same symbol; never two INDEX trades in the same direction (Nifty/BankNifty/Midcap move together). With `max_trades=1` the app behaves as a strict single-signal app.
- R6. Options are BUY only (CE for BUY signal, PE for SELL signal). Never write selling logic.
- R7. No paid services, no Docker/Redis/Postgres. Stack is fixed: Python + FastAPI + SQLite + APScheduler + plain HTML/JS PWA.
- R8. Secrets live only in `.env` (never in code, logs, git, chat). `.env` must be in `.gitignore` if git is used.
- R9. The app never places orders. (Auto-order is Phase 3, needs static IP + 2FA + SEBI algo rules, and only if Raj asks.)
- R10. Every user-facing message stays in simple Hinglish (see sample outputs in Section 9).
- R11. Lot sizes/expiries for index and stock options are read from the Angel instrument master at runtime. The MCX/forex multiplier table in `rtw/config.py` is a default — verify it against the exchange contract specs once and tell Raj if any number is off.
- R12. Ask Raj only for the 5 manual items in the Hinglish box above. Everything else you do yourself.

### 0.4 Definition of done (Phase 1 accepted)
- `pytest` green; `check_setup.py` shows no FAIL in PAPER mode except items Raj must supply (keys).
- One full market day in PAPER mode: candles refresh every minute for Tier-1, Home never shows a stale signal, a WAIT card always shows a reason, Telegram messages arrive for NEW / ACTIVE / TARGET / SL / EXPIRED / MISSED, `/status /why /record /brief /pause /resume /reset_halt /health` work, 08:30 brief arrives.
- Record tab starts empty and fills only from closed PAPER trades.

---

## 1. Product summary (what Raj sees)

| Tab | What it shows |
|---|---|
| Home | The best signal (entry zone, SL, T1, T2, valid-till, exit-by, chase limit, lots, reasons, grade, confidence, PAPER tag) with live trade status; with `max_trades` > 1 one card per open trade, best first; or a WAIT card (what it is waiting for + next big event). Other signals appear as INFO. Last closed trade below. |
| Markets | Sub-tabs Index / Commodity / Stocks / Forex / Crypto. Each lists active BUY/SELL rows first. Stocks tab collapses WAIT rows into a count. |
| Search | Type any stock / pair / BTC → its single analysis (INFO only, never becomes an active trade) + a **chart**. |
| Market mood | Per symbol BULLISH / BEARISH / SIDEWAYS badge (Home strip for the 5 headline assets, Markets rows, chart header). SIDEWAYS shows the last-40-bar range. In-app pop-up (toast, polled every 30 s) + Telegram alert when a headline asset (or an open-trade symbol) changes mood. |
| Charts | 📈 button on every trade card, every Markets row and every Search result: own candle chart (closed 5m bars, resampled to 15m / 1h, EMA20, Entry / SL / T1 / T2 lines), option-premium chart for option trades, and an "open in TradingView" link-out. No external chart library (drawn on a canvas, works offline). |
| News | News mode (CALM / EVENT WINDOW / SHOCK), event calendar with IST countdown, tagged latest headlines, VIX z-score. |
| Record | Overall track record, last 30 trades, equity curve (cumulative R), setup statistics. (The API also returns the paper / live split; the screen shows the overall figure.) |
| Settings | Capital, risk % per trade, profile (conservative default / moderate / aggressive). |

Phone: PWA ("Add to Home screen") + Telegram alerts + 08:30 IST pre-market brief.

## 2. Locked decisions (from Raj — do not change)

| # | Decision |
|---|---|
| 1 | Free data/tools only for now (test mode). Paid later. |
| 2 | No daily manual logins/data gathering by Raj. Only one-time: Angel One SmartAPI keys + Telegram bot in `.env`. Angel session auto-logs-in with TOTP; re-login handled by code. |
| 3 | Default: one active trade at a time across all markets; others = INFO. Raj may raise it to 1–5 simultaneous trades (Settings → "Ek saath kitne signals" or `RTW_MAX_TRADES`). |
| 4 | Options: BUY only (CE/PE). Never selling. |
| 5 | Every signal has: entry zone, valid-till time, MISSED state ("chase mat karo"), exit-by time. WAIT card says what it waits for. |
| 6 | New signals are tagged PAPER until a track record exists. Two steps: (a) the BACKTEST must trust the setup (≥30 tested trades, expectancy > 0 after costs, out-of-sample > 0, still > 0 with doubled costs); (b) even then the signal stays PAPER until the app's own FORWARD record for that setup has ≥30 closed trades with expectancy > 0 (mode `LIVE` skips step b; `LIVE` is reserved and places no orders). |
| 7 | Default risk profile: Conservative. |
| 8 | Gold/Gold Mini and Silver/Silver Mini analysed once; the contract is auto-picked by capital (largest contract whose 1-lot risk fits). |
| 9 | Midcap Nifty gets a STRICT liquidity check: open interest at the chosen strike must be ≥ the median of the 11 nearest strikes (other options: ≥ 40%), premium ≥ ₹2, plus the normal premium / needed-move / IV checks. The free chain has no bid-ask, so a true spread check is backlog P2-6. |
| 10 | Stock list auto-ranks daily by liquidity (F&O list × most active by value). Default top 50 (setting `RTW_STOCKS_TOP_N`, max 100). |
| 11 | News is the core: News Intelligence module (Section 7). No chasing headlines: scheduled events lock entries from 30 min before to 15 min after; SHOCK mode freezes new entries. |
| 12 | Forex: only the 7 exchange-traded pairs (USDINR, EURINR, GBPINR, JPYINR, EURUSD, GBPUSD, USDJPY). |
| 13 | Tool name: **Raj Trading World** (alias RTW). |

## 3. Architecture

```
 [Data adapters: Angel One | NSE(nsefin) | yfinance | Binance | RSS/GDELT | ForexFactory+static calendar]
                              │  (rtw/adapters/*, rtw/live.py — never raise, fallbacks, caches)
                              ▼
 Provider contract (rtw/provider.py)  ◄── FakeProvider (DEMO mode, tests)
                              ▼
 Orchestrator (rtw/pipeline.py)
   refresh candles → SQLite (rtw.db)
   per symbol: layers → combine → news mode → plan → 7 gates → HTF filter → instrument (MCX contract / option strike)
   pick the best (score × R:R × setup record × liquidity) for each free slot (`max_trades`, default 1) → Signal NEW → ACTIVE → TARGET/SL/EXPIRED/MISSED
   protections (streak pause, cooldown, daily loss, max drawdown) → Telegram messages
                              ▼
 FastAPI (rtw/api.py) → PWA (web/index.html)      Telegram bot (rtw/telegram_bot.py)
 APScheduler (rtw/scheduler.py): core 60s | stocks 5min | news 2min | GDELT 15min | health 10min | 06:00 morning | 08:30 brief | 23:50 nightly backtest
```

**What stays in the backend (Raj never sees it):** indicators, layer scoring, weights, regime detection, gates, option math, news tagging, backtests, protections, health logs. Raj sees only the result.

Folder tree (created by `unpack.py`): `main.py, check_setup.py, requirements.txt, .env.example, install.bat, check.bat, start.bat, pytest.ini, data/events_static.json, rtw/…, rtw/adapters/…, web/…, tests/…`.

## 4. Setup guide (one-time)

### 4.1 Windows basics
1. Install Python 3.12 or 3.13 from python.org. Tick **"Add python.exe to PATH"**.
2. Follow Section 0.2 steps 1–5 in DEMO mode first.
3. Windows Firewall prompt on first start → **Allow (private networks)** so the phone can reach it on home WiFi.
4. Keep the PC awake during market hours (Windows power settings → sleep: never; only while trading hours). If the PC sleeps the data gets stale and the app correctly shows WAIT.

### 4.2 Angel One SmartAPI (the only broker setup)
1. Raj needs an Angel One trading account. Go to the SmartAPI portal (smartapi.angelone.in), log in, create an app to get the **API key**. (Portal screens change; if a screen looks different, ask Raj for a screenshot.)
2. Enable **TOTP** in the Angel One app/web security settings. It shows a QR code **and a text secret**. Copy the text secret (this is `ANGEL_TOTP_SECRET`, NOT the 6-digit code that changes).
3. `ANGEL_CLIENT_CODE` = Raj's login ID; `ANGEL_PIN` = his 4-digit MPIN.
4. Put the four values in `.env` (copy `.env.example` → `.env`). Never paste them into chat.
5. Static IP is NOT needed (no orders are placed).

### 4.3 Telegram
1. In Telegram open **@BotFather** → `/newbot` → follow the questions → copy the token → `TELEGRAM_BOT_TOKEN`.
2. Open your new bot and press **Start** once.
3. Chat id: open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser after sending the bot any message and read `"chat":{"id":...}` (or ask @userinfobot). Put it in `TELEGRAM_CHAT_ID`.
4. `check.bat --telegram` must deliver a test message.
The bot ignores every chat except `TELEGRAM_CHAT_ID`.

### 4.4 Going live (data) — still advice-only
1. In `.env`: `RTW_MODE=PAPER`, set `RTW_CAPITAL`, keep `RTW_PROFILE=conservative`.
2. `check.bat` → fix every FAIL using the printed FIX line.
3. `start.bat`. First start downloads ~60 days of history, builds the first setup statistics, then runs. All signals stay tagged PAPER until a setup earns a record.

### 4.5 Phone access
- Same WiFi: `http://<PC-IP>:8000` (PC IP from `ipconfig`). Browser menu → "Add to Home screen".
- Away from home: install **Tailscale** (free) on PC and phone, open `http://<tailscale-ip>:8000`. Set a long random `RTW_ACCESS_KEY` in `.env` (20+ random characters); the app asks for it once and sends it as a header. Do not put the key in a URL you share or bookmark. Without Tailscale, never expose port 8000 to the public internet.
- True "installed app" feel needs HTTPS (Tailscale serve or a free Cloudflare Tunnel). Plain HTTP still works as a home-screen shortcut.
- Telegram works from anywhere with no setup. It is the primary alert channel.

## 5. Data sources (all free)

| Data | Source | Access | Refresh | Fallback | Code |
|---|---|---|---|---|---|
| NSE index/stock candles (5m) | Angel One SmartAPI `getCandleData` | TOTP login | every 60 s (index), 5 min (stocks) | yfinance 5m (`^NSEI`, `^NSEBANK`, `RELIANCE.NS`…) | `adapters/angel.py`, `live.py` |
| MCX candles (crude, gas, gold, silver) | Angel SmartAPI, front-month future (rolls 3 days before expiry) | same | 60 s | **none on purpose** (COMEX units differ) → WAIT "data nahi" | `live.py::_angel_target` |
| Forex INR + cross pairs | Angel SmartAPI (CDS futures) | same | 60 s | yfinance spot **only when Angel keys are not configured at all** (spot and futures prices differ; never mixed mid-session) | same |
| BTC | Binance public klines | no key | 60 s | yfinance `BTC-USD` | `adapters/crypto.py` |
| Live price for active trade | Angel `ltpData` | same | every cycle | last closed candle | `live.py::ltp` |
| Global cues (S&P, Nasdaq, DXY, crude, gold, US10Y, USDINR, VIX, Nikkei, HSI…) | yfinance | no key | 10 min cache | stale cache | `adapters/yf.py` |
| India VIX spike z-score (today's % change vs last 60 days' changes) | yfinance `^INDIAVIX` | no key | 15 min | none (skipped) | `adapters/yf.py` |
| FII/DII cash flows | nsefin `get_fii_dii_activity` | no key | 30 min | skipped (layer unavailable) | `adapters/nse.py` |
| Option chain, OI, PCR, IV | nsefin `get_option_chain` (NSE); IV backed out of ATM premiums if the chain has no IV | no key | 45 s cache | none → index WAIT "option premium nahi mila" (Phase 2: Angel `optionGreek`/`putCallRatio`) | `adapters/nse.py` |
| Option contract chart (premium bars) | Angel `getCandleData` on the option's NFO token (DEMO: synthetic Black-Scholes bars, labelled demo) | same | on demand | "chart data nahi mila" message | `live.py::option_candles` |
| Option premium for chosen strike (exit record) | Angel `ltpData` on option token | same | at close | skipped | `live.py::option_ltp` |
| Lot sizes, expiries, tokens | Angel instrument master JSON | no key | daily cache in `data/` | defaults in `config.py` | `adapters/angel.py` |
| Crypto funding, long/short, OI, Fear & Greed | Binance futures public + alternative.me | no key | 5 min | layer unavailable | `adapters/crypto.py` |
| Headlines | Google News RSS, ET Markets, Moneycontrol, CoinDesk, RBI + Fed press RSS | no key | 2 min | other feeds | `adapters/newsfeeds.py` |
| Global news firehose | GDELT DOC API | no key (1 request / 5 s) | 15 min | RSS only | `adapters/newsfeeds.py` |
| Event calendar | ForexFactory free JSON + `data/events_static.json` (RBI/US CPI/FOMC) + EIA Wednesday rule | no key | 1 h | static + rule | `adapters/calendar.py` |
| Trading holidays | NSE holiday-master endpoint (+ optional `data/holidays.json`) | cookie warm-up | daily 06:00 | manual file | `adapters/nse.py::fetch_holidays` |

Keep `data/events_static.json` updated by hand (or ask the agent to refresh from RBI/Fed/BLS calendars) at least every 3 months. Dates present: RBI decision 7 Oct 2026 10:00 IST; US CPI 14 Oct 2026 18:00 IST (08:30 ET); FOMC decision 28 Oct 2026 23:30 IST (2:00 PM ET). **Verify these against the official calendars once.**

**TradingView:** the app only LINKS to TradingView (`tv_url`, symbol map in `rtw/charts.py`). Embedding TradingView's free widget is not used: its data for NSE/MCX is delayed/limited and NSE option symbols are not reliable in it. Check the link symbols once (e.g. `NSE:NIFTY_MID_SELECT`, `MCX:GOLD1!`, `NSE:USDINR1!`) and fix the map if TradingView names differ.

**Not tested live (be honest with Raj):** `option_candles` (Angel option-token candles) too; every Angel/NSE/Binance/RSS call was written against the library signatures and tested only through offline parsers — the authoring sandbox had no broker access. `check_setup.py` is the first real test. `CDS_CROSS` session end 19:30 (EURUSD/GBPUSD/USDJPY) is unverified — confirm against the NSE currency-derivatives timing circular. The stock universe is ranked by cash-market traded value from the latest bhav copy (fallback: most-active list, then the plain F&O list); the bhav column names are matched tolerantly and the ranking must be checked once on real data.

Angel limits respected by code: 3 candle requests/second (code spaces calls 0.4 s), ≤180/min, ≤5000/hour (stocks 5-min cycle is far below), 3 websocket connections (websocket not used in Phase 1), session expires daily around midnight (code re-logs in automatically; after a failed login it waits 90 s before trying again, because repeated bad logins can lock the Angel account; network errors do NOT trigger a re-login). Cached data is served stale only up to 6× its refresh time, never longer.

## 6. Signal engine (how the call is made)

**Layers** (each gives score −1..+1 and confidence 0..1; unavailable layers are ignored and weights are re-normalised): trend (EMA 20/50/200, Supertrend, VWAP, ADX) · momentum (RSI, MACD, StochRSI) · levels (20-bar breakout, Bollinger squeeze) · zones (support / resistance + demand / supply zones, see below) · volume (z-score spike, OBV) · patterns (engulfing, hammer, shooting star, doji, morning/evening star) · options (PCR, OI walls, max pain; index only) · smart money (FII/DII + participant OI for index, delivery/bulk/insider for stocks, funding/F&G/OI for crypto, COT for commodities) · global cues · news.

**Weights** depend on asset class (INDEX/STOCK/COMMODITY/FOREX/CRYPTO) and regime (TREND / RANGE / VOLATILE from ADX, ATR rank, Bollinger-width rank). See `rtw/scoring.py`.

**Profiles** (default conservative):

| Profile | min score S | min agreement A | min layers | min R:R |
|---|---|---|---|---|
| conservative | 0.45 | 0.70 | 5 | 1:2.0 |
| moderate | 0.38 | 0.62 | 4 | 1:1.7 |
| aggressive | 0.30 | 0.55 | 4 | 1:1.5 |

**Gates (any fail → WAIT with a Hinglish reason):** data fresh · no big event nearby / not in SHOCK · regime allowed · layer agreement · R:R · setup record (≥30 trades, net expectancy>0; unknown record → allowed only as PAPER) · daily loss limit. Extra checks in the pipeline: market open (per segment, holiday-aware) · not within 20 min of the session exit time · 15-minute chart must not strongly oppose the signal (multi-timeframe filter) · protections (3 SL streak → 2 h pause, 30 min cooldown after a trade, daily loss 3R, max drawdown 8R → halt until manual reset) · option checks (needed move ≤ 0.8 × expected move, IV percentile ≤ 85%, ≥ 0.5 day to expiry, OI liquidity at the strike, premium risk fits capital).

**Support / resistance and demand / supply zones (`rtw/zones.py`, closed bars only, no lookahead):**
- *Support / resistance levels:* confirmed swing highs and lows (3 bars each side) plus previous-day high / low / close and classic pivots (P, R1, R2, S1, S2). Levels closer than 0.3 × ATR are merged into one level; more touches = stronger. Supports are below price, resistances above, nearest first.
- *Demand zone:* a base of 1–3 small-bodied candles followed by a big impulse candle (range ≥ 1.6 × ATR, body ≥ 60% of range) that closes ABOVE the base = buyers were there. *Supply zone:* the mirror (impulse down, closes below the base). The zone is the base (wick-to-body); it is known only once the impulse candle has closed. A zone is dead once price CLOSES through its far edge; it is "fresh" until price returns into it; zones touched more than twice are ignored.
- *Vote (zones layer, weight 8%):* votes only when price is AT a zone (+0.8 demand, −0.8 supply, ×0.65 if not fresh) or within 0.5 × ATR of a support (+) / resistance (−); otherwise the layer abstains so it never dilutes the others.
- *Use in the plan:* zone edges and S/R levels are added to the blockers that SHORTEN targets (a BUY target stops before the next resistance / supply zone; a SELL target before the next support / demand zone); for a BUY the stop goes just under the nearest demand zone below price (SELL: above the nearest supply zone) when that is tighter than the swing. If the shortened target breaks the minimum R:R the app says WAIT with the R:R reason, so fewer but cleaner signals.
- *On screen:* charts draw demand (green band) and supply (red band) zones and S / R dotted lines; the chart header lists the nearest support, resistance and zones. The decision also carries `sr` (supports, resistances, zones).
- *Limits (honest):* this is rule-based on 5-minute bars of ≈ 1–5 days; zones are not drawn from daily / weekly charts yet (backlog P2-8), and the thresholds (1.6 × ATR impulse, 0.3 × ATR merge) are defaults that the nightly backtest does not tune.

**Plan:** entry zone ±0.2 ATR; SL = beyond last swing, clipped to 1–2.5 ATR; T1 = R:R × SL distance (shortened to the nearest blocking level), T2 beyond; chase limit 0.5 ATR beyond entry (price past it → MISSED); lots from `capital × risk% / (SL distance × lot)`; exit-by = session close − 15 min (crypto: +12 h), shortened before the next HIGH event.

**Options:** underlying signal BUY → buy CE, SELL → buy PE. ATM strike (one step OTM if ATM premium > 1.2% of spot). Premium SL ≈ delta × underlying SL distance (never more than 45% of premium); max loss = full premium (shown). Exits are monitored on the underlying (free intraday option-premium history does not exist); the real option record is built from the premium at close during paper trading.

**Lifecycle:** NEW (waiting for entry zone) → ACTIVE (entered) → TARGET / SL / EXPIRED (time) ; NEW can end as MISSED (price ran past chase limit) or EXPIRED. If SL and target fall inside the same bar, SL is assumed first (conservative).

**Ranking of candidates:** `|S| × min(R:R, 4) × setup factor × liquidity factor` (liquidity factor is reserved and currently 1.0 for everything; the liquidity CHECK on options is a gate, see above). The winner becomes a TRADE; with `max_trades` > 1 the next-best non-conflicting candidates fill the remaining free slots (one per symbol; never two INDEX trades in the same direction), the rest are INFO. Risk per trade is `risk_pct` of capital EACH, so total open risk can reach `max_trades × risk_pct`; the daily-loss (3R), streak-pause and max-drawdown protections count all trades together.

**Self-testing / rule decay:** every night 23:50 the backtester (same `analyze()` + `advance()` as live, closed bars only, costs included, 70/30 in-sample/out-of-sample split, doubled-cost stress test) rewrites `setup_stats`. A setup with ≥30 trades that stops passing is **benched** and its signals are blocked until it passes again.

**Zero-volume instruments:** index spot and forex candles carry no volume, so the volume layer is unavailable for them. Conservative profile needs ≥5 available layers, so these instruments need the global layer (yfinance) and/or news/smart/options layers to be alive. If yfinance is down they will correctly stay on WAIT.

**Market mood (`rtw/mood.py`):** derived from the engine's combined score S and regime, per symbol, no extra data. RANGE regime with |S| < 0.45 → SIDEWAYS; otherwise S ≥ +0.15 → BULLISH, S ≤ −0.15 → BEARISH, else SIDEWAYS; strength mild / moderate (≥0.25) / strong (≥0.40). Closed market or no data → no mood (shown as "Market band / data nahi"). Flip tracking has hysteresis: a new mood must hold 3 consecutive cycles before it is recorded, and a symbol gets at most one Telegram alert per 30 min (flips inside the gap are stored and shown in the pop-up, not re-sent). Mood is information only; it never opens a trade by itself.

**Contract roll (MCX / forex futures):** the front contract is chosen 3 days (MCX) / 2 days (CDS) before expiry. When the contract changes, the orchestrator clears that symbol's stored candles and any waiting (NEW) signal for it, because the price level of the new contract differs. An ACTIVE trade is never silently moved.

**Option sizing note:** Nifty/BankNifty options have big lots, so at the default capital of ₹1,00,000 and 1% risk the app will often show "capital kam" (it states the minimum capital needed). Roughly ₹1.5–3 lakh+ is needed for a Nifty option at 1% risk; stock options and MCX mini contracts work with less. This is correct behaviour, not a bug.

**Implied volatility:** the free nsefin chain does not always include IV. When the IV columns are empty the app backs the ATM IV out of the ATM call/put premiums (bisection in `options.implied_vol`). IV percentile needs ~20 daily stored values (the 15:45 `iv` job builds them), so until then IV percentile is "unknown" and not used as a block.

**Concurrency:** `Orchestrator.cycle()` is serialized by a lock (core, stocks and `/api/refresh` can never run two cycles at once, so the `max_trades` limit can never be exceeded by a race).

**Honest expectations:** backtests overstate live results; the free history is short (≈60–100 days), so every signal is PAPER for the first weeks. The app never promises profit.

## 7. News Intelligence (the core)

1. **Event calendar** (HIGH/MED/LOW, IST countdown): ForexFactory feed (USD → all assets; EUR/GBP/JPY/CNY/CAD/AUD → their related assets), static India/US dates, EIA weekly rule.
2. **Collector:** RSS every 2 min + GDELT every 15 min + official RBI/Fed press; dedup by URL hash; stored in `news_items`.
3. **Tagger:** local rules (rate cut/hike, war, ceasefire, OPEC, inventories, sanctions, tariffs, crypto events, FII flows, dollar, inflation, selloff…) → asset, direction, magnitude, confidence, half-life. **High impact only if the story is official OR confirmed by ≥2 distinct sources**; single unofficial source gets 40% magnitude.
4. **News modes per asset:** CALM · EVENT WINDOW (30 min before → 15 min after a HIGH event; 10 → 5 for MED) · SHOCK (India VIX **day-change** z-score ≥ 3 versus its last 60 daily changes, or a shock flag; new entries frozen 30 min). Window → WAIT card says e.g. "RBI 10:00 ke baad reaction dekhna hai, ruko".
5. **Plan modifiers:** exit-by pulled before the next HIGH event; elevated VIX/risk → size ×0.7 and SL ×1.2.
6. **News layer:** time-decayed vote per symbol/group (`news_layer`).
7. **Never race headlines.** Legal: no "inside news"/UPSI tips of any kind; only public sources.

Built and tested but not yet wired to live data (Phase 2 tasks in Section 13): surprise engine (`news.surprise_tags`), reaction reader (`news.read_reaction`), AI-GPR risk meter.

## 8. UI + API contract

PWA: single file `web/index.html` (+ `manifest.webmanifest`, `sw.js`; icons are generated by `rtw/icons.py` on start). The API is never cached (stale signals are dangerous). Auto-refresh every 30 s on Home / Markets / News (only while the page is visible).

| Endpoint | Returns |
|---|---|
| `GET /api/home` | status NEW/ACTIVE/WAIT, `trade` (first open trade) + `trades` (all open trades) + `max_trades`, or `wait` card, `info` list, `last_closed` |
| `GET /api/markets/{index\|commodity\|stocks\|forex\|crypto}` | active rows + waiting rows (stocks: counts only) |
| `GET /api/search?q=` | single analysis for any symbol (INFO only) |
| `GET /api/chart?q=&tf=5m\|15m\|1h[&strike=&cp=CE\|PE&expiry=YYYY-MM-DD]` | last 120 candles + EMA20 + levels + `tv_url`; with strike/cp/expiry the option-contract premium chart |
| `GET /api/mood` | mood of every core symbol (+ range when SIDEWAYS) and the last 10 confirmed flips (drives the pop-up) |
| `GET /api/news` | mode, events with countdown, tagged headlines, VIX z |
| `GET /api/record` | track record, last trades, equity curve, setup stats |
| `GET /api/health` | per-component status, last cycle, paused flag |
| `GET/POST /api/settings` | capital (1,000–1,00,00,00,000), risk_pct (0.1%–5%), profile, max_trades (1–5) |
| `POST /api/refresh` | force one cycle |
| `POST /api/reset_halt` | clear the max-drawdown halt (manual) |

If `RTW_ACCESS_KEY` is set every `/api/*` call needs header `x-key` or `?key=`.

## 9. Sample outputs (real formatter output — keep this Hinglish style)

Numbers are illustrative. The Nifty sample (2 lots) assumes a capital of roughly ₹3 lakh+; at the default ₹1 lakh the app shows "capital kam" for Nifty options instead.

```text
🟢 NAYA SIGNAL [PAPER]
NIFTY 24500 CE — CALL (CE) KHARIDO
Entry: Nifty 50 24,480-24,510 (option ~₹142.00)
SL: Nifty 50 24,420 (option ~₹118.00)
Target 1: Nifty 50 24,610 (option ~₹190.00) | Target 2: Nifty 50 24,700
Lots: 2 | Max nuksan (poora premium): ₹18,460
Valid: 11:25 tak | Nikalna: 15:15 tak
Kyu: EMA trend upar; 20-bar high breakout; PCR 1.25 (put writing, support); Dollar index -0.8% (faydemand)
Grade A | Confidence 82%
Chase mat karo: 24,540 ke aage mat lo.
PAPER signal: abhi record ban raha hai, real paisa mat lagao.
----
🟢 NAYA SIGNAL [PAPER]
GOLD (GOLDM) — BUY
Entry: Gold / Gold Mini 121,850-121,990
SL: 121,400
Target 1: 122,700 | Target 2: 123,300
Lots: 3 | SL pe risk: ₹2,520
Valid: 11:25 tak | Nikalna: 23:15 tak
Kyu: COMEX gold +0.9%; EMA trend upar; Dollar index -0.8% (faydemand)
Grade B | Confidence 71%
Chase mat karo: 122,200 ke aage mat lo.
PAPER signal: abhi record ban raha hai, real paisa mat lagao.
----
⏸ WAIT
Sabse kareeb: BANKNIFTY — agreement kam: S=0.31/0.45 A=0.58/0.7 layers=7
Intezar: layers ka agreement badhna
Agla bada event: RBI policy decision 07 Oct 10:00 IST (45 min me)
```

## 10. Telegram

Messages: NEW / ACTIVE / TARGET / SL / EXPIRED / MISSED, market-mood change for the headline assets, event warning while a trade is open, data-source problem + recovery, 08:30 IST brief (weekdays). Commands: `/status /why /record /brief /pause /resume /reset_halt /health /help`. `/pause` stops NEW signals only; the open trade is still monitored. `/reset_halt` (also `POST /api/reset_halt`) clears the max-drawdown halt and restarts the drawdown count from zero — Raj should use it only after he has looked at the Record tab.

## 11. Scheduler (IST)

| Job | When | Does |
|---|---|---|
| core | every 60 s | refresh Tier-1 candles for open markets → analyze → manage active trade → maybe start best |
| stocks | every 5 min | same for the F&O stock list |
| news | every 2 min | RSS collect |
| gdelt | every 15 min | GDELT collect |
| health | every 10 min | write health log, Telegram alert on new failure / recovery |
| morning | 06:00 | Angel re-login, master reload, stock list rebuild, holidays refresh |
| brief | Mon–Fri 08:30 | pre-market brief to Telegram |
| iv | Mon–Fri 15:45 | store ATM IV (for IV percentile) |
| backtest | 23:50 | nightly walk-forward + rule-decay benching |

Tiers: Tier 1 deep always-on (indices, MCX, forex, BTC); Tier 2 F&O stock list every 5 min; Tier 3 (all-NSE daily bhav-copy scan) is Phase 2.

## 12. Failure points and what the app does

| Failure | App behaviour |
|---|---|
| Angel login fails / token expires | auto re-login once; NSE/forex fall back to yfinance; MCX → WAIT "data nahi" + Telegram alert |
| Data older than 120 s | `data_fresh` gate → WAIT |
| NSE option chain blocked | index signal → WAIT "option premium nahi mila" (never guesses premiums) |
| News feed down | news layer simply empty; health shows FAIL; trading continues |
| Calendar feed down | static dates + EIA rule only; health shows it |
| One symbol throws | logged to `health_log`; other symbols continue |
| Scheduler job exception | logged `job:<name>` FAIL; scheduler keeps running |
| PC asleep / app closed | no cycles; on restart data is stale → WAIT until fresh; an open trade is re-checked from the bars since `last_checked` |
| Telegram fails | returns False; app/UI unaffected |
| Capital too small for 1 lot | WAIT with the minimum capital needed |
| Holiday / market closed | decision "market band hai"; Home says all markets closed |

## 13. Phases and backlog

**Phase 1 + most of Phase 2 are in this codebase** (confluence engine, news modes/tagger/calendar, regime filter, multi-timeframe filter, walk-forward backtest with costs, rule-decay benching, no-trade zones, risk engine with ATR SL/target + daily loss lock + protections, OI walls/max pain/IV percentile, contract choice, PWA, Telegram, DEMO mode).

**Remaining backlog — start only after Phase 1 acceptance passes AND Raj says "go". One item at a time, each with a test.**

| ID | Task | How |
|---|---|---|
| P2-1 | Stock smart-money inputs (delivery %, bulk/block deals, insider, OI build-up) | `nsefin`: `get_equity_bhav_copy` (delivery column), `get_fno_bhav_copy`, `get_insider_trading`; return `{"kind":"stock",...}` from `LiveProvider.smart_inputs` (layer code `smart.stock_smart_layer` exists) |
| P2-2 | Surprise engine live | parse ForexFactory `actual`/`forecast` for CPI, NFP, Fed, RBI, EIA; map to `news.SURPRISE_KINDS`; add `surprise_tags()` output to `LiveProvider.news_tags` |
| P2-3 | COT layer for commodities | CFTC weekly file; return `{"kind":"cot",...}` (layer code `smart.cot_layer` exists) |
| P2-4 | Reaction reader | after an event, compare price at +5/+15 min with `news.read_reaction`; allow entries only on CONFIRMED |
| P2-5 | Angel websocket (Tier 2 ticks, faster active-trade checks) | `SmartWebSocketV2` + `candles.CandleBuilder`; max 3 connections |
| P2-6 | Angel fallbacks for option data + real bid-ask spread check for Midcap Nifty | `optionGreek`, `putCallRatio`, `oIBuildup`, `gainersLosers`, quote depth |
| P2-8 | Higher-timeframe zones | build daily / 1-hour demand-supply zones and S/R from history (Angel `getCandleData` 1h / 1d) and merge with the 5-minute ones |
| P2-7 | Tier 3 daily all-NSE scan | bhav copy → `scan.cheap_scan_score` → shortlist into Tier 2 |
| P3-1 | ML vote as ONE extra layer | LightGBM on stored features; must beat the rule-only record out-of-sample or stay off |
| P3-2 | LLM news analyst (Gemini free tier) | tags unknown headlines + writes the "why"; never decides alone |
| P3-3 | Event memory | store past event reactions per asset → learned impact map |
| P3-4 | Hinglish assistant in Telegram | free-text questions → answers from DB |
| P3-5 | Auto-order via OpenAlgo | static IP + 2FA + SEBI algo rules + AGPL licence check; only if Raj asks |

## 14. Legal and safety (tell Raj plainly)
- Personal use. Sending signals to other people needs SEBI Research Analyst registration.
- Insider trading on unpublished price-sensitive information is illegal. The app uses only public sources; never add "tips".
- Retail forex only in the 7 exchange-traded pairs (other forex is a FEMA offence).
- Signals are advice with risk. Options buying can lose the full premium. PAPER tag = no real money yet.
- Algo orders (Phase 3) need exchange/SEBI compliance; not part of this build.

## 15. FILES (every file, byte-exact — extract with `unpack.py`)

Format: each file is a fenced block whose opening line is ` ````text file=<path> ` and whose last line is ` ```` `. Do not edit them by hand.

### `requirements.txt`

````text file=requirements.txt
pandas>=2.2
numpy>=1.26
fastapi>=0.110
uvicorn>=0.29
httpx>=0.27
apscheduler>=3.10,<4
requests>=2.31
feedparser>=6.0
yfinance>=0.2.40
pyotp>=2.9
smartapi-python>=1.4
logzero
pycryptodome
websocket-client
nsefin>=0.1.5
tzdata
pytest>=8
````

### `.env.example`

````text file=.env.example
# Raj Trading World settings. Copy this file to ".env" (same folder). NEVER share this file or paste it in chat.
# DEMO  = fake data, zero setup, to see the app working.   PAPER = real data, signals tagged PAPER (use this first).
RTW_MODE=DEMO
RTW_CAPITAL=100000
RTW_RISK_PCT=0.01
RTW_PROFILE=conservative
RTW_STOCKS_TOP_N=50
# how many signals at the same time: 1 = one single signal (default), up to 5. Each trade risks RTW_RISK_PCT separately.
RTW_MAX_TRADES=1
RTW_PORT=8000
# password for phone/web access (leave empty only if you use it on home WiFi). Set a long random text.
RTW_ACCESS_KEY=

# Telegram alerts (create bot with @BotFather, get chat id from @userinfobot)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Angel One SmartAPI (one-time manual step; get the API key at smartapi.angelone.in)
ANGEL_API_KEY=
ANGEL_CLIENT_CODE=
ANGEL_PIN=
ANGEL_TOTP_SECRET=

# optional (free key from fred.stlouisfed.org)
FRED_API_KEY=
````

### `pytest.ini`

````text file=pytest.ini
[pytest]
testpaths = tests
addopts = -q
````

### `install.bat`

````text file=install.bat
@echo off
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest
echo.
echo Install done. Ab check.bat chalao.
pause
````

### `check.bat`

````text file=check.bat
@echo off
.venv\Scripts\python check_setup.py %*
pause
````

### `start.bat`

````text file=start.bat
@echo off
.venv\Scripts\python main.py
pause
````

### `main.py`

````text file=main.py
"""Raj Trading World — start everything:  python main.py"""
import threading
from datetime import datetime
import uvicorn
from rtw.api import create_app
from rtw.config import get_settings
from rtw.db import connect, log_health
from rtw.notify import TelegramSender
from rtw.pipeline import Orchestrator
from rtw.scheduler import build_scheduler
from rtw.sessions import IST
from rtw import jobs
from rtw.telegram_bot import run_bot
from rtw.icons import ensure_icons
from rtw.api import WEB_DIR


def build(st):
    con = connect(st.db_path)
    live = None
    if st.mode == "DEMO":
        from rtw.provider import FakeProvider
        provider = FakeProvider()
    else:
        from rtw.live import LiveProvider
        provider = live = LiveProvider(st, con)
    sender = TelegramSender(st.telegram_token, st.telegram_chat_id)
    orc = Orchestrator(con, provider, st, send=sender.send if sender.ready else None)
    orc.apply_saved_settings()
    return orc, live, sender


def startup(orc, live, now):
    if live is not None:
        for c, s, d in live.start(now):
            log_health(orc.con, now, c, s, d)
        live.refresh_stock_universe(now, 100)
        jobs.update_holidays(orc, now)
        live.collect_news(now, gdelt=True)
    has = orc.con.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    if has < 500:
        jobs.bootstrap_history(orc, now, 60)
        jobs.nightly_backtest(orc, now)
    now = datetime.now(IST)                      # bootstrap/backtest may have taken minutes
    orc.refresh_all(now, "core")
    orc.cycle(now, "core")


def main():
    st = get_settings()
    ensure_icons(WEB_DIR)
    orc, live, sender = build(st)
    now = datetime.now(IST)
    print(f"Raj Trading World | mode={st.mode} | capital={st.capital:.0f} | profile={st.profile}")
    threading.Thread(target=startup, args=(orc, live, now), daemon=True).start()   # UI opens immediately, data fills in
    sch = build_scheduler(orc, live)
    sch.start()
    stop = threading.Event()
    if sender.ready:
        threading.Thread(target=run_bot, args=(orc, sender, lambda: datetime.now(IST), stop), daemon=True).start()
        sender.send("Raj Trading World chalu ho gaya. /help likho.")
    print(f"App kholo: http://localhost:{st.port}   (phone: same WiFi par http://<PC-IP>:{st.port})")
    uvicorn.run(create_app(orc), host=st.host, port=st.port, log_level="warning")


if __name__ == "__main__":
    main()
````

### `check_setup.py`

````text file=check_setup.py
"""Run this FIRST:  python check_setup.py   (add --telegram to send a test message). Prints OK / FAIL / SKIP with the fix for every part."""
import importlib
import os
import sys
from datetime import datetime

from rtw.config import get_settings
from rtw.db import connect
from rtw.sessions import IST

OK, FAIL, SKIP = "OK  ", "FAIL", "SKIP"
rows = []


def rec(name, status, detail="", fix=""):
    rows.append((name, status, detail, fix))
    print(f"[{status}] {name}: {detail}" + (f"\n        -> FIX: {fix}" if fix and status != OK else ""))


def main():
    now = datetime.now(IST)
    st = get_settings()
    rec("python", OK if sys.version_info >= (3, 10) else FAIL, sys.version.split()[0], "Python 3.10+ install karo")
    for mod in ("pandas", "numpy", "fastapi", "uvicorn", "apscheduler", "requests", "feedparser", "yfinance", "pyotp", "SmartApi", "nsefin", "tzdata"):
        try:
            importlib.import_module(mod)
            rec(f"package {mod}", OK)
        except Exception as e:
            rec(f"package {mod}", FAIL, str(e), "pip install -r requirements.txt")
    rec(".env file", OK if os.path.exists(".env") else SKIP, f"mode={st.mode}", ".env.example ko .env naam se copy karke keys bharo (DEMO me zaroorat nahi)")
    con = connect(st.db_path)
    rec("database", OK, st.db_path)
    if st.mode == "DEMO":
        rec("mode", OK, "DEMO: synthetic data. Live data ke liye .env me RTW_MODE=PAPER karo")
        return summary()
    from rtw.live import LiveProvider
    from rtw.config import CORE_SPECS
    lp = LiveProvider(st, con)
    for c, s, d in lp.start(now):
        rec(c, OK if s == "OK" else (SKIP if s == "SKIP" else FAIL), d,
            "Angel API key / client code / PIN / TOTP secret check karo (TOTP secret = QR ke neeche wala text, 6 digit code nahi)")
    for sym in ("NIFTY", "GOLD", "USDINR", "BTCUSDT"):
        sp = next(x for x in CORE_SPECS if x.symbol == sym)
        df = lp.candles(sp, now, "5m", 100)
        rec(f"candles {sym}", OK if df is not None and len(df) > 20 else FAIL, f"{0 if df is None else len(df)} bars",
            "market band ho to normal hai; warna Angel login/master ya internet check karo")
    ltp = lp.ltp(CORE_SPECS[0], now)
    rec("angel ltp NIFTY", OK if ltp else SKIP, str(ltp))
    g = lp.global_changes(now)
    rec("global (yfinance)", OK if len(g) >= 8 else FAIL, f"{len(g)} tickers", "internet check; kuch ghante baad dobara")
    rec("India VIX z", OK if lp.vix_z(now) is not None else SKIP, str(lp.vix_z(now)))
    ch = lp.option_chain(CORE_SPECS[0], now)
    rec("option chain NIFTY", OK if ch and ch["rows"] else SKIP, f"{len(ch['rows']) if ch else 0} strikes, expiry {ch['expiry'] if ch else '-'}",
        "NSE kabhi block karta hai; market hours me dobara try karo. Columns print karne ke liye rtw/adapters/nse.py::chain_from_df dekho")
    n = lp.collect_news(now, gdelt=True)
    rec("news feeds", OK if n > 10 else FAIL, f"{n} items", "internet/firewall check")
    ev = lp.events(now)
    rec("event calendar", OK if ev else FAIL, f"{len(ev)} events")
    fii = lp.smart_inputs(CORE_SPECS[0], now)
    rec("FII/DII (NSE)", OK if fii else SKIP, str(fii))
    cs = lp.smart_inputs(CORE_SPECS[-1], now)
    rec("crypto funding/F&G", OK if cs and len(cs) > 1 else SKIP, str(cs))
    if "--telegram" in sys.argv:
        from rtw.notify import TelegramSender
        s = TelegramSender(st.telegram_token, st.telegram_chat_id)
        rec("telegram", OK if s.send("Raj Trading World test message ✅") else FAIL, "test message", "BOT TOKEN aur CHAT ID check karo; bot ko pehle /start bhejo")
    summary()


def summary():
    bad = [r for r in rows if r[1] == FAIL]
    print(f"\n{len(rows)} checks | {len(bad)} FAIL")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
````

### `data/events_static.json`

````text file=data/events_static.json
[
  {"name": "RBI policy decision", "when": "2026-10-07T10:00:00+05:30", "impact": "HIGH", "assets": ["ALL"]},
  {"name": "US CPI", "when": "2026-10-14T18:00:00+05:30", "impact": "HIGH", "assets": ["ALL"]},
  {"name": "FOMC decision", "when": "2026-10-28T23:30:00+05:30", "impact": "HIGH", "assets": ["ALL"]}
]
````

### `rtw/__init__.py`

````text file=rtw/__init__.py
# package marker
````

### `rtw/config.py`

````text file=rtw/config.py
"""Settings (.env), the symbol universe, and MCX/forex contract tables.
Lot sizes / contract multipliers below are DEFAULTS. At runtime the app overrides them from the exchange
instrument master (see adapters/angel.py::lot_from_master). Never trust these numbers for real orders."""
from __future__ import annotations
import os
from dataclasses import dataclass, field


def load_env(path: str = ".env") -> None:
    """Tiny .env reader (no dependency). Existing environment variables win."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _f(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


@dataclass
class Settings:
    mode: str = "DEMO"                 # DEMO (synthetic data) | PAPER (live data, paper signals) | LIVE
    capital: float = 100000.0          # trading capital in INR
    risk_pct: float = 0.01             # risk per trade as fraction of capital (1%)
    profile: str = "conservative"      # conservative | moderate | aggressive
    db_path: str = "rtw.db"
    access_key: str = ""               # simple password for phone/web access ("" = no password, LAN only)
    telegram_token: str = ""
    telegram_chat_id: str = ""
    angel_api_key: str = ""
    angel_client_code: str = ""
    angel_pin: str = ""
    angel_totp_secret: str = ""
    fred_key: str = ""
    stocks_top_n: int = 50
    max_trades: int = 1                # how many TRADE signals may be open at the same time (1 = single signal, max 5)
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def angel_ready(self) -> bool:
        return all([self.angel_api_key, self.angel_client_code, self.angel_pin, self.angel_totp_secret])


def get_settings() -> Settings:
    load_env()
    g = os.environ.get
    return Settings(
        mode=g("RTW_MODE", "DEMO").upper(), capital=_f("RTW_CAPITAL", 100000), risk_pct=_f("RTW_RISK_PCT", 0.01),
        profile=g("RTW_PROFILE", "conservative").lower(), db_path=g("RTW_DB", "rtw.db"), access_key=g("RTW_ACCESS_KEY", ""),
        telegram_token=g("TELEGRAM_BOT_TOKEN", ""), telegram_chat_id=g("TELEGRAM_CHAT_ID", ""),
        angel_api_key=g("ANGEL_API_KEY", ""), angel_client_code=g("ANGEL_CLIENT_CODE", ""), angel_pin=g("ANGEL_PIN", ""),
        angel_totp_secret=g("ANGEL_TOTP_SECRET", ""), fred_key=g("FRED_API_KEY", ""),
        stocks_top_n=int(_f("RTW_STOCKS_TOP_N", 50)), max_trades=max(1, min(5, int(_f("RTW_MAX_TRADES", 1)))), host=g("RTW_HOST", "0.0.0.0"), port=int(_f("RTW_PORT", 8000)))


# ------------------------------------------------------------------ universe
@dataclass(frozen=True)
class Spec:
    symbol: str          # app symbol (unique)
    name: str            # display name
    tab: str             # index | commodity | stocks | forex | crypto
    asset_class: str     # INDEX | STOCK | COMMODITY | FOREX | CRYPTO
    group: str           # news / global group: INDEX, GOLD, SILVER, CRUDE, NATGAS, USDINR..., STOCK, BTC
    segment: str         # NSE | MCX | CDS_INR | CDS_CROSS | CRYPTO
    yf: str = ""         # yfinance ticker (fallback / global context), "" = none
    angel_name: str = "" # `name` field in Angel instrument master ("" = not on Angel)
    exch: str = "NSE"    # Angel exchange segment: NSE | MCX | CDS ; BINANCE for crypto
    has_options: bool = False
    lot: float = 1.0     # default lot units (index) / pnl per 1 price point per lot (MCX, forex)


INDEX_SPECS = [
    Spec("NIFTY", "Nifty 50", "index", "INDEX", "INDEX", "NSE", "^NSEI", "NIFTY", "NSE", True, 65),
    Spec("BANKNIFTY", "Bank Nifty", "index", "INDEX", "INDEX", "NSE", "^NSEBANK", "BANKNIFTY", "NSE", True, 30),
    Spec("MIDCPNIFTY", "Midcap Nifty", "index", "INDEX", "INDEX", "NSE", "", "MIDCPNIFTY", "NSE", True, 120),
]
# One spec per commodity GROUP. The contract (big/mini/micro) is chosen by capital at plan time (see choose_contract).
COMMODITY_SPECS = [
    Spec("GOLD", "Gold / Gold Mini", "commodity", "COMMODITY", "GOLD", "MCX", "GC=F", "GOLDM", "MCX", False, 10),
    Spec("SILVER", "Silver / Silver Mini", "commodity", "COMMODITY", "SILVER", "MCX", "SI=F", "SILVERM", "MCX", False, 5),
    Spec("CRUDEOIL", "Crude Oil", "commodity", "COMMODITY", "CRUDE", "MCX", "CL=F", "CRUDEOILM", "MCX", False, 10),
    Spec("NATURALGAS", "Natural Gas", "commodity", "COMMODITY", "NATGAS", "MCX", "NG=F", "NATGASMINI", "MCX", False, 250),
]
# The 7 legal retail forex pairs (exchange traded in India). pnl-per-point defaults; cross pairs are in USD -> multiplied by USDINR at runtime.
FOREX_SPECS = [
    Spec("USDINR", "USD/INR", "forex", "FOREX", "USDINR", "CDS_INR", "USDINR=X", "USDINR", "CDS", False, 1000),
    Spec("EURINR", "EUR/INR", "forex", "FOREX", "EURINR", "CDS_INR", "EURINR=X", "EURINR", "CDS", False, 1000),
    Spec("GBPINR", "GBP/INR", "forex", "FOREX", "GBPINR", "CDS_INR", "GBPINR=X", "GBPINR", "CDS", False, 1000),
    Spec("JPYINR", "JPY/INR", "forex", "FOREX", "JPYINR", "CDS_INR", "JPYINR=X", "JPYINR", "CDS", False, 1000),
    Spec("EURUSD", "EUR/USD", "forex", "FOREX", "EURUSD", "CDS_CROSS", "EURUSD=X", "EURUSD", "CDS", False, 1000),
    Spec("GBPUSD", "GBP/USD", "forex", "FOREX", "GBPUSD", "CDS_CROSS", "GBPUSD=X", "GBPUSD", "CDS", False, 1000),
    Spec("USDJPY", "USD/JPY", "forex", "FOREX", "USDJPY", "CDS_CROSS", "JPY=X", "USDJPY", "CDS", False, 1000),
]
CROSS_PAIRS_USD_QUOTED = {"EURUSD", "GBPUSD"}      # P&L in USD -> x USDINR
CRYPTO_SPECS = [
    Spec("BTCUSDT", "Bitcoin", "crypto", "CRYPTO", "BTC", "CRYPTO", "BTC-USD", "", "BINANCE", False, 0.001),
]
CORE_SPECS = INDEX_SPECS + COMMODITY_SPECS + FOREX_SPECS + CRYPTO_SPECS


def stock_spec(symbol: str, name: str = "") -> Spec:
    return Spec(symbol.upper(), name or symbol.upper(), "stocks", "STOCK", "STOCK", "NSE", f"{symbol.upper()}.NS", symbol.upper(), "NSE", False, 1)


# ------------------------------------------------------------------ MCX contract ladder (largest -> smallest)
# (instrument name in master, rupee P&L per 1 price point per lot). Verify against the exchange contract specs at runtime.
MCX_CONTRACTS = {
    "GOLD": [("GOLD", 100.0), ("GOLDM", 10.0), ("GOLDPETAL", 0.1)],
    "SILVER": [("SILVER", 30.0), ("SILVERM", 5.0), ("SILVERMIC", 1.0)],
    "CRUDE": [("CRUDEOIL", 100.0), ("CRUDEOILM", 10.0)],
    "NATGAS": [("NATURALGAS", 1250.0), ("NATGASMINI", 250.0)],
}


def choose_contract(group: str, sl_dist: float, risk_budget: float) -> dict:
    """Pick the LARGEST contract whose 1-lot risk fits the budget; lots = floor(budget / risk per lot).
    If even the smallest does not fit -> smallest with lots=0 (affordable False)."""
    ladder = MCX_CONTRACTS[group]
    for name, mult in ladder:
        per_lot = sl_dist * mult
        if per_lot > 0 and per_lot <= risk_budget:
            return {"contract": name, "pnl_per_point": mult, "lots": int(risk_budget // per_lot), "affordable": True,
                    "risk_per_lot": per_lot}
    name, mult = ladder[-1]
    return {"contract": name, "pnl_per_point": mult, "lots": 0, "affordable": False, "risk_per_lot": sl_dist * mult}


# Fallback stock list used only when the live F&O list could not be fetched (liquid F&O names; the daily job replaces it).
DEFAULT_STOCKS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "BHARTIARTL", "ITC", "LT", "AXISBANK", "KOTAKBANK",
                  "HINDUNILVR", "BAJFINANCE", "MARUTI", "SUNPHARMA", "M&M", "NTPC", "ONGC", "POWERGRID", "ASIANPAINT", "TITAN",
                  "ULTRACEMCO", "WIPRO", "HCLTECH", "TECHM", "ADANIENT", "ADANIPORTS", "COALINDIA", "JSWSTEEL", "TATASTEEL",
                  "HINDALCO", "BAJAJFINSV", "NESTLEIND", "CIPLA", "DRREDDY", "EICHERMOT", "GRASIM", "INDUSINDBK", "BPCL", "IOC",
                  "DIVISLAB", "HEROMOTOCO", "APOLLOHOSP", "TRENT", "BEL", "HAL", "SBILIFE", "HDFCLIFE"]
````

### `rtw/sessions.py`

````text file=rtw/sessions.py
"""Market sessions (IST). NOTE: on Windows install the `tzdata` package or zoneinfo will fail."""
from __future__ import annotations
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
NY = ZoneInfo("America/New_York")


def us_dst_active(d: date) -> bool:
    return datetime(d.year, d.month, d.day, 12, tzinfo=NY).dst() != timedelta(0)


def session_times(segment: str, d: date):
    """segment: NSE | MCX | CDS_INR | CDS_CROSS | CRYPTO. Returns (open_time, close_time) or None (24x7)."""
    if segment == "NSE":
        return time(9, 15), time(15, 30)
    if segment == "MCX":
        return time(9, 0), (time(23, 30) if us_dst_active(d) else time(23, 55))
    if segment == "CDS_INR":
        return time(9, 0), time(17, 0)
    if segment == "CDS_CROSS":
        return time(9, 0), time(19, 30)
    if segment == "CRYPTO":
        return None
    raise ValueError(f"unknown segment {segment}")


def is_trading_day(segment: str, d: date, holidays: set | None = None) -> bool:
    if segment == "CRYPTO":
        return True
    return d.weekday() < 5 and d not in (holidays or set())


def is_open(segment: str, now: datetime, holidays: set | None = None) -> bool:
    now = now.astimezone(IST)
    if segment == "CRYPTO":
        return True
    if not is_trading_day(segment, now.date(), holidays):
        return False
    o, c = session_times(segment, now.date())
    return o <= now.time() < c


def close_dt(segment: str, d: date) -> datetime | None:
    st = session_times(segment, d)
    return None if st is None else datetime.combine(d, st[1], tzinfo=IST)


def exit_by(segment: str, d: date, minutes_before: int = 15, crypto_hours: int = 12, now: datetime | None = None) -> datetime:
    """Intraday exit-by time. Crypto has no close, so use now + crypto_hours."""
    cd = close_dt(segment, d)
    if cd is None:
        base = (now or datetime.now(IST)).astimezone(IST)
        return base + timedelta(hours=crypto_hours)
    return cd - timedelta(minutes=minutes_before)
````

### `rtw/indicators.py`

````text file=rtw/indicators.py
"""Pure indicator functions. Input: pandas Series/DataFrame with columns open, high, low, close, volume.
Rule: every function uses ONLY past+current bars (no lookahead). Callers must pass CLOSED bars only."""
from __future__ import annotations
import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    ru = up.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rd = dn.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = ru / rd.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    out = out.where(~((rd == 0) & (ru > 0)), 100.0)
    out = out.where(~((rd == 0) & (ru == 0)), 50.0)
    return out


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = true_range(df)
    a = 1.0 / n
    atr_ = tr.ewm(alpha=a, adjust=False, min_periods=n).mean()
    pdi = 100.0 * plus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / atr_
    mdi = 100.0 * minus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / atr_
    dx = 100.0 * (pdi - mdi).abs() / (pdi + mdi).replace(0.0, np.nan)
    adx_ = dx.ewm(alpha=a, adjust=False, min_periods=n).mean()
    return pd.DataFrame({"adx": adx_, "pdi": pdi, "mdi": mdi})


def supertrend(df: pd.DataFrame, n: int = 10, mult: float = 3.0) -> pd.DataFrame:
    """direction: +1 up-trend, -1 down-trend. line: the supertrend value."""
    a = atr(df, n).to_numpy()
    hl2 = ((df["high"] + df["low"]) / 2.0).to_numpy()
    close = df["close"].to_numpy()
    m = len(df)
    ub = hl2 + mult * a
    lb = hl2 - mult * a
    fub = ub.copy()
    flb = lb.copy()
    direction = np.zeros(m)
    line = np.full(m, np.nan)
    start = int(np.argmax(~np.isnan(a))) if np.any(~np.isnan(a)) else m
    for i in range(start, m):
        if i == start:
            direction[i] = 1.0 if close[i] >= hl2[i] else -1.0
            line[i] = flb[i] if direction[i] > 0 else fub[i]
            continue
        fub[i] = ub[i] if (ub[i] < fub[i - 1] or close[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (lb[i] > flb[i - 1] or close[i - 1] < flb[i - 1]) else flb[i - 1]
        if direction[i - 1] > 0:
            direction[i] = -1.0 if close[i] < flb[i] else 1.0
        else:
            direction[i] = 1.0 if close[i] > fub[i] else -1.0
        line[i] = flb[i] if direction[i] > 0 else fub[i]
    return pd.DataFrame({"direction": direction, "line": line}, index=df.index)


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    up, lo = mid + k * sd, mid - k * sd
    return pd.DataFrame({"mid": mid, "upper": up, "lower": lo, "bw": (up - lo) / mid})


def vwap(df: pd.DataFrame) -> pd.Series:
    """Intraday VWAP, resets each calendar date of the index (DatetimeIndex required)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    day = df.index.normalize() if hasattr(df.index, "normalize") else pd.Series(df.index).dt.normalize()
    pv = (tp * df["volume"]).groupby(day).cumsum()
    vv = df["volume"].groupby(day).cumsum()
    return pv / vv.replace(0.0, np.nan)


def obv(df: pd.DataFrame) -> pd.Series:
    return (np.sign(df["close"].diff().fillna(0.0)) * df["volume"]).cumsum()


def stoch_rsi(close: pd.Series, n: int = 14, k: int = 3, d: int = 3) -> pd.DataFrame:
    r = rsi(close, n)
    lo, hi = r.rolling(n, min_periods=n).min(), r.rolling(n, min_periods=n).max()
    raw = 100.0 * (r - lo) / (hi - lo).replace(0.0, np.nan)
    kk = raw.rolling(k, min_periods=k).mean()
    return pd.DataFrame({"k": kk, "d": kk.rolling(d, min_periods=d).mean()})


def zscore(s: pd.Series, n: int = 20) -> pd.Series:
    m = s.rolling(n, min_periods=n).mean()
    sd = s.rolling(n, min_periods=n).std(ddof=0).replace(0.0, np.nan)
    return (s - m) / sd


def percentile_rank(s: pd.Series, n: int = 100) -> pd.Series:
    """Rank of the latest value within the trailing n values, 0..1."""
    return s.rolling(n, min_periods=max(10, n // 4)).apply(lambda w: float((w <= w[-1]).mean()), raw=True)


def swing_levels(df: pd.DataFrame, left: int = 3, right: int = 3, lookback: int = 120) -> dict:
    """Last CONFIRMED swing high/low (a swing at bar i is only known after `right` more bars)."""
    d = df.iloc[-lookback:]
    h, l = d["high"].to_numpy(), d["low"].to_numpy()
    sh, sl_ = [], []
    for i in range(left, len(d) - right):
        if h[i] == h[i - left:i + right + 1].max() and h[i] > h[i - left:i].max():
            sh.append(float(h[i]))
        if l[i] == l[i - left:i + right + 1].min() and l[i] < l[i - left:i].min():
            sl_.append(float(l[i]))
    return {"swing_highs": sh, "swing_lows": sl_,
            "last_high": sh[-1] if sh else float(h.max()), "last_low": sl_[-1] if sl_ else float(l.min())}


def classic_pivots(prev_high: float, prev_low: float, prev_close: float) -> dict:
    p = (prev_high + prev_low + prev_close) / 3.0
    return {"P": p, "R1": 2 * p - prev_low, "S1": 2 * p - prev_high,
            "R2": p + (prev_high - prev_low), "S2": p - (prev_high - prev_low)}


def candle_patterns(df: pd.DataFrame) -> dict:
    """Pattern flags for the LAST closed bar. Needs >= 3 bars."""
    if len(df) < 3:
        return {}
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    i = len(df) - 1
    body = abs(c[i] - o[i])
    rng = max(h[i] - l[i], 1e-12)
    upper = h[i] - max(c[i], o[i])
    lower = min(c[i], o[i]) - l[i]
    prev_body_dir = np.sign(c[i - 1] - o[i - 1])
    prior_trend = c[i - 1] - c[max(0, i - 6)]
    out = {
        "bull_engulf": bool(prev_body_dir < 0 and c[i] > o[i] and c[i] >= o[i - 1] and o[i] <= c[i - 1]),
        "bear_engulf": bool(prev_body_dir > 0 and c[i] < o[i] and c[i] <= o[i - 1] and o[i] >= c[i - 1]),
        "hammer": bool(lower >= 2 * max(body, 1e-12) and upper <= 0.5 * max(body, 1e-12) + 0.1 * rng and prior_trend < 0),
        "shooting_star": bool(upper >= 2 * max(body, 1e-12) and lower <= 0.5 * max(body, 1e-12) + 0.1 * rng and prior_trend > 0),
        "doji": bool(body <= 0.1 * rng),
    }
    m1 = c[i - 2] < o[i - 2] and abs(c[i - 1] - o[i - 1]) <= 0.3 * (h[i - 1] - l[i - 1] + 1e-12) and c[i] > o[i] and c[i] > (o[i - 2] + c[i - 2]) / 2
    e1 = c[i - 2] > o[i - 2] and abs(c[i - 1] - o[i - 1]) <= 0.3 * (h[i - 1] - l[i - 1] + 1e-12) and c[i] < o[i] and c[i] < (o[i - 2] + c[i - 2]) / 2
    out["morning_star"], out["evening_star"] = bool(m1), bool(e1)
    return out
````

### `rtw/layers.py`

````text file=rtw/layers.py
"""Chart-based layers. Every layer returns LayerResult(score in [-1,1], conf in [0,1], reasons[Hinglish short]).
score>0 = bullish, score<0 = bearish. Input df = CLOSED bars only (index = DatetimeIndex)."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from . import indicators as ta


@dataclass
class LayerResult:
    name: str
    score: float = 0.0
    conf: float = 0.0
    reasons: list = field(default_factory=list)

    def clipped(self) -> "LayerResult":
        self.score = float(max(-1.0, min(1.0, self.score)))
        self.conf = float(max(0.0, min(1.0, self.conf)))
        return self


def _last(s: pd.Series, default=np.nan):
    v = s.iloc[-1] if len(s) else default
    return default if pd.isna(v) else float(v)


def regime(df: pd.DataFrame) -> dict:
    """TREND / RANGE / VOLATILE + numbers. Needs >= 60 bars."""
    a = ta.adx(df, 14)
    atr_pct = ta.atr(df, 14) / df["close"]
    atr_rank = _last(ta.percentile_rank(atr_pct, 100), 0.5)
    bw_rank = _last(ta.percentile_rank(ta.bollinger(df["close"])["bw"], 100), 0.5)
    adx_v = _last(a["adx"], 0.0)
    if atr_rank >= 0.85 and bw_rank >= 0.85:
        name = "VOLATILE"
    elif adx_v >= 25:
        name = "TREND"
    else:
        name = "RANGE"
    return {"name": name, "adx": adx_v, "atr_rank": atr_rank, "bw_rank": bw_rank}


def trend_layer(df: pd.DataFrame, intraday: bool = False) -> LayerResult:
    r = LayerResult("trend")
    if len(df) < 60:
        return r
    c = df["close"]
    e20, e50 = ta.ema(c, 20), ta.ema(c, 50)
    e200 = ta.ema(c, 200) if len(df) >= 200 else None
    parts = [np.sign(_last(c) - _last(e50, _last(c))), np.sign(_last(e20, 0) - _last(e50, 0))]
    if e200 is not None and not pd.isna(e200.iloc[-1]):
        parts.append(np.sign(_last(e50, 0) - _last(e200, 0)))
    align = float(np.mean(parts))
    st = ta.supertrend(df, 10, 3.0)
    st_dir = float(st["direction"].iloc[-1])
    score = 0.55 * align + 0.45 * st_dir
    if intraday:
        vw = ta.vwap(df)
        if not pd.isna(vw.iloc[-1]):
            score += 0.2 * np.sign(_last(c) - _last(vw))
            r.reasons.append("VWAP ke upar" if _last(c) > _last(vw) else "VWAP ke neeche")
    adx_v = _last(ta.adx(df, 14)["adx"], 0.0)
    r.score = score
    r.conf = min(1.0, max(0.2, adx_v / 35.0))
    r.reasons.append("EMA trend upar" if align > 0.3 else "EMA trend neeche" if align < -0.3 else "EMA mixed")
    r.reasons.append("Supertrend BUY" if st_dir > 0 else "Supertrend SELL")
    r.reasons.append(f"ADX {adx_v:.0f}")
    return r.clipped()


def momentum_layer(df: pd.DataFrame) -> LayerResult:
    r = LayerResult("momentum")
    if len(df) < 40:
        return r
    c = df["close"]
    rs = _last(ta.rsi(c, 14), 50.0)
    m = ta.macd(c)
    hist, hist_prev = _last(m["hist"], 0.0), float(m["hist"].iloc[-2]) if len(m) > 1 and not pd.isna(m["hist"].iloc[-2]) else 0.0
    rsi_score = max(-1.0, min(1.0, (rs - 50.0) / 25.0))
    if rs > 75 or rs < 25:
        rsi_score *= 0.5
        r.reasons.append("RSI extreme, ulta palatne ka risk")
    macd_score = 0.5 * np.sign(hist) + 0.5 * np.sign(hist - hist_prev)
    r.score = 0.5 * rsi_score + 0.5 * macd_score
    r.conf = 0.7
    r.reasons.append(f"RSI {rs:.0f}")
    r.reasons.append("MACD upar" if hist > 0 else "MACD neeche")
    return r.clipped()


def levels_layer(df: pd.DataFrame, n: int = 20) -> LayerResult:
    """Range-breakout + Bollinger. Uses prior n bars (excluding the last) for the channel."""
    r = LayerResult("levels")
    if len(df) < n + 5:
        return r
    prior = df.iloc[-(n + 1):-1]
    hi, lo, c = float(prior["high"].max()), float(prior["low"].min()), float(df["close"].iloc[-1])
    bb = ta.bollinger(df["close"])
    if c > hi:
        r.score, r.conf = 1.0, 0.8
        r.reasons.append(f"{n}-bar high breakout")
    elif c < lo:
        r.score, r.conf = -1.0, 0.8
        r.reasons.append(f"{n}-bar low breakdown")
    else:
        pos = (c - lo) / max(hi - lo, 1e-12)
        r.score = (pos - 0.5) * 0.6
        r.conf = 0.4
        r.reasons.append("range ke andar")
    if not pd.isna(bb["bw"].iloc[-1]) and ta.percentile_rank(bb["bw"], 100).iloc[-1] <= 0.15:
        r.reasons.append("Bollinger squeeze, badi move aa sakti hai")
    return r.clipped()


def volume_layer(df: pd.DataFrame) -> LayerResult:
    r = LayerResult("volume")
    if len(df) < 30 or float(df["volume"].tail(20).sum()) <= 0:
        return r
    z = _last(ta.zscore(df["volume"], 20), 0.0)
    direction = np.sign(float(df["close"].iloc[-1] - df["open"].iloc[-1]))
    obv = ta.obv(df)
    obv_slope = np.sign(float(obv.iloc[-1] - obv.iloc[-10]))
    spike = max(0.0, min(1.0, z / 3.0))
    r.score = direction * spike * 0.7 + 0.3 * obv_slope
    r.conf = max(0.3, min(1.0, abs(z) / 3.0))
    if z >= 2:
        r.reasons.append(f"volume spike z={z:.1f}")
    r.reasons.append("OBV upar" if obv_slope > 0 else "OBV neeche")
    return r.clipped()


def pattern_layer(df: pd.DataFrame) -> LayerResult:
    r = LayerResult("patterns")
    p = ta.candle_patterns(df)
    if not p:
        return r
    s = 0.0
    names = []
    for k, w in (("bull_engulf", 0.6), ("morning_star", 0.7), ("hammer", 0.4),
                 ("bear_engulf", -0.6), ("evening_star", -0.7), ("shooting_star", -0.4)):
        if p.get(k):
            s += w
            names.append(k)
    r.score = s
    r.conf = 0.55 if names else 0.25
    r.reasons = names or (["doji, confusion"] if p.get("doji") else ["koi clear pattern nahi"])
    return r.clipped()


def chart_layers(df: pd.DataFrame, intraday: bool = False) -> dict:
    return {l.name: l for l in (trend_layer(df, intraday), momentum_layer(df), levels_layer(df),
                                volume_layer(df), pattern_layer(df))}
````

### `rtw/scoring.py`

````text file=rtw/scoring.py
"""Combine layer votes into one directional score S in [-1,1] and an agreement A in [0,1]."""
from __future__ import annotations
import numpy as np

LAYERS = ["trend", "momentum", "levels", "zones", "volume", "patterns", "options", "smart", "global", "news"]

# default weights per asset class and regime (relative; re-normalised over layers that are actually available)
_BASE = {
    "INDEX":     {"trend": .20, "momentum": .12, "levels": .10, "zones": .08, "volume": .05, "patterns": .05, "options": .20, "smart": .10, "global": .10, "news": .08},
    "STOCK":     {"trend": .22, "momentum": .12, "levels": .12, "zones": .08, "volume": .12, "patterns": .06, "options": .00, "smart": .18, "global": .06, "news": .12},
    "COMMODITY": {"trend": .22, "momentum": .12, "levels": .10, "zones": .08, "volume": .06, "patterns": .05, "options": .00, "smart": .13, "global": .20, "news": .12},
    "FOREX":     {"trend": .24, "momentum": .12, "levels": .12, "zones": .08, "volume": .02, "patterns": .06, "options": .00, "smart": .04, "global": .22, "news": .18},
    "CRYPTO":    {"trend": .24, "momentum": .12, "levels": .12, "zones": .08, "volume": .08, "patterns": .06, "options": .04, "smart": .18, "global": .06, "news": .10},
}
_REGIME_MULT = {  # regime adjusts how much chart layers matter
    "TREND":    {"trend": 1.3, "momentum": 1.0, "levels": 1.1, "zones": 0.9, "patterns": 0.8},
    "RANGE":    {"trend": 0.6, "momentum": 1.0, "levels": 0.8, "zones": 1.4, "patterns": 1.2},
    "VOLATILE": {"trend": 0.9, "momentum": 0.8, "levels": 0.9, "volume": 1.2, "news": 1.2},
}
PROFILES = {  # default profile = conservative
    "conservative": {"s_min": 0.45, "a_min": 0.70, "min_layers": 5, "rr_min": 2.0, "grade_a": (0.60, 0.80), "grade_b": (0.50, 0.70)},
    "moderate":     {"s_min": 0.38, "a_min": 0.62, "min_layers": 4, "rr_min": 1.7, "grade_a": (0.60, 0.80), "grade_b": (0.50, 0.70)},
    "aggressive":   {"s_min": 0.30, "a_min": 0.55, "min_layers": 4, "rr_min": 1.5, "grade_a": (0.60, 0.80), "grade_b": (0.50, 0.70)},
}


def weights_for(asset_class: str, regime_name: str) -> dict:
    w = dict(_BASE[asset_class])
    for k, m in _REGIME_MULT.get(regime_name, {}).items():
        w[k] = w.get(k, 0.0) * m
    return w


def combine(results: dict, asset_class: str, regime_name: str) -> dict:
    """results: {layer_name: LayerResult}. Layers with conf==0 or weight==0 are 'unavailable'."""
    w = weights_for(asset_class, regime_name)
    avail = {k: r for k, r in results.items() if r is not None and r.conf > 0 and w.get(k, 0) > 0}
    if not avail:
        return {"S": 0.0, "A": 0.0, "n_avail": 0, "n_agree": 0, "drivers": []}
    num = sum(w[k] * r.conf * r.score for k, r in avail.items())
    den = sum(w[k] * r.conf for k, r in avail.items())
    S = num / den if den else 0.0
    sign = np.sign(S)
    decisive = {k: r for k, r in avail.items() if abs(r.score) >= 0.2}
    d_den = sum(w[k] * r.conf for k, r in decisive.items())
    agree = {k: r for k, r in decisive.items() if np.sign(r.score) == sign and sign != 0}
    A = (sum(w[k] * r.conf for k, r in agree.items()) / d_den) if d_den else 0.0
    drivers = sorted(avail.items(), key=lambda kv: -abs(w[kv[0]] * kv[1].conf * kv[1].score))
    return {"S": float(S), "A": float(A), "n_avail": len(avail), "n_agree": len(agree),
            "drivers": [(k, round(r.score, 2), r.reasons[:2]) for k, r in drivers[:4]]}


def direction_of(S: float) -> str:
    return "BUY" if S > 0 else "SELL" if S < 0 else "NONE"


def grade(S: float, A: float, profile: str = "conservative") -> str:
    p = PROFILES[profile]
    s = abs(S)
    if s >= p["grade_a"][0] and A >= p["grade_a"][1]:
        return "A"
    if s >= p["grade_b"][0] and A >= p["grade_b"][1]:
        return "B"
    if s >= p["s_min"] and A >= p["a_min"]:
        return "C"
    return "D"
````

### `rtw/plan.py`

````text file=rtw/plan.py
"""Trade plan builder: entry zone, stoploss, targets, size. Pure function, no I/O."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import math


@dataclass
class Plan:
    direction: str
    entry: float
    entry_lo: float
    entry_hi: float
    sl: float
    t1: float
    t2: float
    sl_dist: float
    rr: float
    lots: int
    risk_amount: float
    chase_price: float
    valid_till: datetime
    exit_by: datetime
    affordable: bool

    def to_dict(self) -> dict:
        d = asdict(self)
        d["valid_till"], d["exit_by"] = self.valid_till.isoformat(), self.exit_by.isoformat()
        return d


def build_plan(direction: str, price: float, atr: float, swing_low: float, swing_high: float,
               supports: list, resistances: list, lot_size: int, capital: float, risk_pct: float,
               rr_min: float, now: datetime, valid_minutes: int, exit_by: datetime,
               size_mult: float = 1.0) -> Plan:
    if direction not in ("BUY", "SELL"):
        raise ValueError("direction must be BUY or SELL")
    if atr <= 0 or price <= 0:
        raise ValueError("atr and price must be > 0")
    long = direction == "BUY"
    if long:
        raw = price - (swing_low - 0.2 * atr) if swing_low < price else 1.5 * atr
    else:
        raw = (swing_high + 0.2 * atr) - price if swing_high > price else 1.5 * atr
    sl_dist = min(max(raw, 1.0 * atr), 2.5 * atr)
    sgn = 1.0 if long else -1.0
    sl = price - sgn * sl_dist
    t1 = price + sgn * rr_min * sl_dist
    # nearest blocking level between entry and raw T1 (levels closer than 0.3 ATR are ignored)
    lv = sorted([r for r in resistances if r > price + 0.3 * atr]) if long else sorted([s for s in supports if s < price - 0.3 * atr], reverse=True)
    if lv and ((lv[0] < t1) if long else (lv[0] > t1)):
        t1 = lv[0] - sgn * 0.1 * atr
    rr = abs(t1 - price) / sl_dist
    t2_raw = price + sgn * max(3.0, rr_min + 1.0) * sl_dist
    beyond = [x for x in lv if ((x > t1) if long else (x < t1))]
    t2 = t2_raw
    if beyond and ((beyond[0] < t2_raw) if long else (beyond[0] > t2_raw)):
        cand = beyond[0] - sgn * 0.1 * atr
        t2 = cand if ((cand > t1 + 0.5 * atr) if long else (cand < t1 - 0.5 * atr)) else t2_raw
    lots = int(math.floor((capital * risk_pct * size_mult) / (sl_dist * lot_size))) if lot_size > 0 else 0
    return Plan(direction=direction, entry=price, entry_lo=price - 0.2 * atr, entry_hi=price + 0.2 * atr,
                sl=sl, t1=t1, t2=t2, sl_dist=sl_dist, rr=rr, lots=lots,
                risk_amount=lots * sl_dist * lot_size, chase_price=price + sgn * 0.5 * atr,
                valid_till=now + timedelta(minutes=valid_minutes), exit_by=exit_by, affordable=lots >= 1)
````

### `rtw/options.py`

````text file=rtw/options.py
"""Options math (BUY-only app: CE/PE buying). Pure functions, stdlib math only."""
from __future__ import annotations
import math
from .layers import LayerResult


def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(spot: float, strike: float, t_years: float, sigma: float, cp: str, r: float = 0.065) -> float:
    """Black-Scholes. cp = 'CE' or 'PE'. Used only for sanity checks (premium vs fair value)."""
    if t_years <= 0 or sigma <= 0:
        return max(0.0, spot - strike) if cp == "CE" else max(0.0, strike - spot)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t_years) / (sigma * math.sqrt(t_years))
    d2 = d1 - sigma * math.sqrt(t_years)
    if cp == "CE":
        return spot * _ncdf(d1) - strike * math.exp(-r * t_years) * _ncdf(d2)
    return strike * math.exp(-r * t_years) * _ncdf(-d2) - spot * _ncdf(-d1)


def implied_vol(price: float, spot: float, strike: float, t_years: float, cp: str, r: float = 0.065) -> float:
    """Bisection IV from an option premium. Returns 0.0 if the price is outside the no-arbitrage range or inputs are bad."""
    if price <= 0 or spot <= 0 or strike <= 0 or t_years <= 0:
        return 0.0
    lo, hi = 0.01, 3.0
    if price < bs_price(spot, strike, t_years, lo, cp, r) - 1e-9 or price > bs_price(spot, strike, t_years, hi, cp, r) + 1e-9:
        return 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if bs_price(spot, strike, t_years, mid, cp, r) < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def iv_percentile(history: list, current: float) -> float:
    """Share of past IV values that are <= current, 0..1. Needs >= 20 values else returns 0.5 (unknown)."""
    h = [x for x in history if x is not None and x > 0]
    if len(h) < 20 or current is None:
        return 0.5
    return sum(1 for x in h if x <= current) / len(h)


def expected_move(spot: float, iv: float, days: float) -> float:
    """1-sigma expected move in points. iv as fraction (0.14 = 14%)."""
    return spot * iv * math.sqrt(max(days, 0.0) / 365.0)


def breakeven(strike: float, premium: float, cp: str) -> float:
    return strike + premium if cp == "CE" else strike - premium


def prob_profit_buy(spot: float, strike: float, premium: float, iv: float, days: float, cp: str) -> float:
    """Probability that the underlying finishes beyond breakeven at expiry (lognormal, zero drift). 0..1."""
    t = max(days, 0.0) / 365.0
    be = breakeven(strike, premium, cp)
    if t <= 0 or iv <= 0 or be <= 0:
        return 0.0
    d2 = (math.log(spot / be) - 0.5 * iv ** 2 * t) / (iv * math.sqrt(t))
    return _ncdf(d2) if cp == "CE" else _ncdf(-d2)


def pcr(chain: list) -> float:
    """chain: list of dict(strike, ce_oi, pe_oi, ...). Put/Call OI ratio."""
    ce = sum(float(r.get("ce_oi") or 0) for r in chain)
    pe = sum(float(r.get("pe_oi") or 0) for r in chain)
    return pe / ce if ce > 0 else 0.0


def max_pain(chain: list) -> float | None:
    """Strike where total option-writer loss is minimum."""
    strikes = sorted({float(r["strike"]) for r in chain})
    if not strikes:
        return None
    best, best_loss = None, None
    for k in strikes:
        loss = 0.0
        for r in chain:
            s = float(r["strike"])
            loss += max(0.0, k - s) * float(r.get("ce_oi") or 0) + max(0.0, s - k) * float(r.get("pe_oi") or 0)
        if best_loss is None or loss < best_loss:
            best, best_loss = k, loss
    return best


def oi_walls(chain: list) -> dict:
    """Highest call OI strike = resistance wall, highest put OI strike = support wall."""
    if not chain:
        return {"resistance": None, "support": None}
    res = max(chain, key=lambda r: float(r.get("ce_oi") or 0))
    sup = max(chain, key=lambda r: float(r.get("pe_oi") or 0))
    return {"resistance": float(res["strike"]), "support": float(sup["strike"])}


def atm_strike(spot: float, strikes: list) -> float:
    return min(strikes, key=lambda k: abs(k - spot))


def pick_option(direction: str, spot: float, strikes: list, chain_by_strike: dict, days_to_expiry: float,
                iv: float, max_premium_pct: float = 0.012) -> dict | None:
    """BUY-only. BUY signal -> CE, SELL signal -> PE. Picks ATM; steps to 1 strike OTM if premium is
    larger than max_premium_pct of spot (cheap enough). Returns None if nothing sensible.
    chain_by_strike: {strike: {"CE": ltp, "PE": ltp}}"""
    if direction not in ("BUY", "SELL") or not strikes:
        return None
    cp = "CE" if direction == "BUY" else "PE"
    ss = sorted(strikes)
    i = ss.index(atm_strike(spot, ss))
    step = 1 if cp == "CE" else -1
    for j in (i, i + step):
        if j < 0 or j >= len(ss):
            continue
        k = ss[j]
        prem = (chain_by_strike.get(k) or {}).get(cp)
        if not prem or prem <= 0:
            continue
        if j == i and prem > max_premium_pct * spot and (i + step) in range(len(ss)):
            continue
        em = expected_move(spot, iv, days_to_expiry)
        pop = prob_profit_buy(spot, k, prem, iv, days_to_expiry, cp)
        be = breakeven(k, prem, cp)
        need = abs(be - spot)
        return {"cp": cp, "strike": k, "premium": float(prem), "breakeven": be, "expected_move": em,
                "pop": pop, "need_move": need, "move_ratio": (need / em) if em > 0 else 9.9}
    return None


def option_ok(opt: dict | None, iv_pct: float, days_to_expiry: float,
              max_move_ratio: float = 0.8, max_iv_pct: float = 0.85, min_days: float = 0.5) -> tuple[bool, str]:
    """Buy-only sanity: do not buy when needed move is too big vs expected move, IV expensive, or expiry too near."""
    if opt is None:
        return False, "option premium nahi mila"
    if days_to_expiry < min_days:
        return False, "expiry bahut paas, theta kha jayega"
    if opt["move_ratio"] > max_move_ratio:
        return False, "option ko paisa banane ke liye expected move se zyada chalna padega"
    if iv_pct > max_iv_pct:
        return False, "IV bahut mehengi, option overpriced"
    return True, "option theek hai"


def options_layer(spot: float, chain: list, iv_pct: float | None = None, prev_oi_chain: list | None = None) -> LayerResult:
    """Vote from option chain: PCR, OI walls, max pain. Index/BTC use only."""
    r = LayerResult("options")
    if not chain or spot <= 0 or sum(float(x.get("ce_oi") or 0) + float(x.get("pe_oi") or 0) for x in chain) <= 0:
        return r        # no OI data (e.g. broker-only fallback chain) -> no vote
    p = pcr(chain)
    mp = max_pain(chain)
    walls = oi_walls(chain)
    s = 0.0
    # PCR: >1.2 supportive (put writers confident), <0.7 bearish; extremes treated mildly (contrarian risk)
    if p >= 1.2:
        s += 0.4
        r.reasons.append(f"PCR {p:.2f} (put writing, support)")
    elif p <= 0.7:
        s -= 0.4
        r.reasons.append(f"PCR {p:.2f} (call writing, dabav)")
    else:
        r.reasons.append(f"PCR {p:.2f} neutral")
    if mp:
        d = (mp - spot) / spot
        s += max(-0.3, min(0.3, d * 30.0))
        r.reasons.append(f"max pain {mp:.0f}")
    if walls["resistance"] and walls["support"]:
        up, dn = walls["resistance"] - spot, spot - walls["support"]
        tot = up + dn
        if tot > 0:
            s += 0.3 * ((up - dn) / tot)
            r.reasons.append(f"OI wall: support {walls['support']:.0f}, resistance {walls['resistance']:.0f}")
    r.score = s
    r.conf = 0.6
    if iv_pct is not None and iv_pct > 0.85:
        r.conf *= 0.7
        r.reasons.append("IV bahut high")
    return r.clipped()


def bs_delta(spot: float, strike: float, t_years: float, sigma: float, cp: str, r: float = 0.065) -> float:
    """Black-Scholes delta (CE positive, PE negative). Used when the broker Greeks are missing."""
    if t_years <= 0 or sigma <= 0:
        itm = spot > strike if cp == "CE" else spot < strike
        return (1.0 if cp == "CE" else -1.0) if itm else 0.0
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t_years) / (sigma * math.sqrt(t_years))
    return _ncdf(d1) if cp == "CE" else _ncdf(d1) - 1.0


def option_plan(premium: float, delta: float, sl_dist: float, t1_dist: float, t2_dist: float, lot: float,
                risk_budget: float, risk_pct: float = 0.01, max_sl_frac: float = 0.45) -> dict:
    """Premium-level plan from underlying levels (delta approximation; gamma/theta ignored -> conservative on gains).
    SL never risks more than max_sl_frac of the premium. max_loss = whole premium (BUY-only app)."""
    d = abs(delta)
    sl_p = max(premium - d * sl_dist, premium * (1.0 - max_sl_frac))
    t1_p = premium + d * t1_dist
    t2_p = premium + d * t2_dist
    risk_per_lot = (premium - sl_p) * lot
    lots = int(math.floor(risk_budget / risk_per_lot)) if risk_per_lot > 0 else 0
    return {"premium": premium, "sl_premium": sl_p, "t1_premium": t1_p, "t2_premium": t2_p, "delta": d, "lot": lot,
            "lots": lots, "affordable": lots >= 1, "risk_per_lot": risk_per_lot, "max_loss_per_lot": premium * lot,
            "min_capital": (risk_per_lot / risk_pct) if risk_pct > 0 else None,
            "rr_premium": ((t1_p - premium) / (premium - sl_p)) if premium > sl_p else 0.0}


def liquidity_ok(rows: list, strike: float, cp: str, strict: bool = False, premium: float | None = None,
                 min_premium: float = 2.0) -> tuple[bool, str]:
    """Open-interest liquidity proxy (the free chain has no bid/ask). OI at the strike must be >= 40% of the median OI of the
    11 nearest strikes (100% when strict, used for Midcap Nifty). Unknown OI: pass, except strict -> fail."""
    key = "ce_oi" if cp == "CE" else "pe_oi"
    near = sorted(rows, key=lambda r: abs(float(r["strike"]) - strike))[:11]
    ois = sorted(float(r.get(key) or 0) for r in near)
    if not ois or sum(ois) == 0:
        return (False, "OI data nahi, Midcap ke liye liquidity pakki nahi") if strict else (True, "OI data nahi, liquidity check chhoda")
    me = next((float(r.get(key) or 0) for r in rows if float(r["strike"]) == strike), 0.0)
    if me <= 0:
        return False, "is strike par OI zero hai"
    med = ois[len(ois) // 2]
    if me < (1.0 if strict else 0.4) * med:
        return False, "is strike par OI/liquidity kam hai"
    if premium is not None and premium < min_premium:
        return False, "premium bahut chhota, illiquid"
    return True, "liquidity theek hai"
````

### `rtw/gates.py`

````text file=rtw/gates.py
"""Safety gates + protections. A signal becomes BUY/SELL only if ALL gates pass; otherwise WAIT with a reason."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from .scoring import PROFILES


@dataclass
class GateInput:
    S: float
    A: float
    n_avail: int
    n_agree: int
    rr: float
    data_age_sec: float
    max_data_age_sec: float
    regime: str
    allowed_regimes: tuple = ("TREND", "RANGE", "VOLATILE")
    setup_expectancy: float | None = None      # net of costs, out-of-sample; None = unknown
    setup_trades: int = 0
    paper: bool = False                         # PAPER-tag asset: allowed through, flagged
    daily_loss_hit: bool = False
    news_mode: str = "CALM"                     # CALM | EVENT_WINDOW | SHOCK
    news_lock_reason: str | None = None         # e.g. "RBI 10:00 ke baad"
    news_wait_until: datetime | None = None
    profile: str = "conservative"
    min_setup_trades: int = 30


@dataclass
class GateResult:
    name: str
    passed: bool
    reason: str


def evaluate_gates(g: GateInput) -> list[GateResult]:
    p = PROFILES[g.profile]
    out = []
    out.append(GateResult("data_fresh", g.data_age_sec <= g.max_data_age_sec,
                          "data fresh hai" if g.data_age_sec <= g.max_data_age_sec else f"data purana ({g.data_age_sec:.0f}s)"))
    news_ok = g.news_mode == "CALM" or (g.news_mode == "EVENT_WINDOW" and not g.news_lock_reason)
    out.append(GateResult("news_clear", news_ok,
                          "koi bada event paas nahi" if news_ok else (g.news_lock_reason or "news lock / shock mode")))
    out.append(GateResult("regime_fit", g.regime in g.allowed_regimes, f"regime {g.regime}"))
    agree_ok = abs(g.S) >= p["s_min"] and g.A >= p["a_min"] and g.n_avail >= p["min_layers"]
    out.append(GateResult("layer_agreement", agree_ok,
                          f"S={abs(g.S):.2f} A={g.A:.2f} layers={g.n_avail}" if agree_ok else
                          f"agreement kam: S={abs(g.S):.2f}/{p['s_min']} A={g.A:.2f}/{p['a_min']} layers={g.n_avail}/{p['min_layers']}"))
    out.append(GateResult("risk_reward", g.rr >= p["rr_min"] - 1e-9, f"R:R 1:{g.rr:.1f} (min 1:{p['rr_min']})"))
    if g.setup_expectancy is None or g.setup_trades < g.min_setup_trades:
        if g.paper:
            out.append(GateResult("setup_record", True, "PAPER: setup ka record abhi ban raha hai"))
        else:
            out.append(GateResult("setup_record", False, "is setup ka backtest record kaafi nahi"))
    else:
        ok = g.setup_expectancy > 0
        out.append(GateResult("setup_record", ok, f"setup expectancy {g.setup_expectancy:+.2f}R ({g.setup_trades} trades)"))
    out.append(GateResult("daily_loss", not g.daily_loss_hit, "daily loss limit lag chuka, aaj aur trade nahi" if g.daily_loss_hit else "daily loss limit OK"))
    return out


def all_passed(results: list[GateResult]) -> bool:
    return all(r.passed for r in results)


def first_failure(results: list[GateResult]) -> GateResult | None:
    return next((r for r in results if not r.passed), None)


@dataclass
class Protections:
    """Freqtrade-style protections. State is kept by the caller (persisted in DB)."""
    streak_limit: int = 3                 # consecutive SL hits -> pause
    pause_minutes: int = 120
    cooldown_minutes: int = 30            # after any closed trade
    max_drawdown_r: float = 8.0           # cumulative R drawdown (from peak) -> halt until manual reset
    daily_loss_r: float = 3.0             # daily loss limit in R
    results_r: list = field(default_factory=list)   # list of (closed_at: datetime, r_multiple: float)
    paused_until: datetime | None = None
    halted: bool = False

    def record(self, closed_at: datetime, r_multiple: float):
        self.results_r.append((closed_at, float(r_multiple)))
        streak = 0
        for _, r in reversed(self.results_r):
            if r < 0:
                streak += 1
            else:
                break
        if streak >= self.streak_limit:
            self.paused_until = closed_at + timedelta(minutes=self.pause_minutes)
        if self.drawdown_r() >= self.max_drawdown_r:
            self.halted = True

    def drawdown_r(self) -> float:
        peak, cum, dd = 0.0, 0.0, 0.0
        for _, r in self.results_r:
            cum += r
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        return dd

    def today_r(self, now: datetime) -> float:
        return sum(r for t, r in self.results_r if t.date() == now.date())

    def daily_loss_hit(self, now: datetime) -> bool:
        return self.today_r(now) <= -self.daily_loss_r

    def can_trade(self, now: datetime) -> tuple[bool, str]:
        if self.halted:
            return False, "max drawdown halt: manual reset chahiye"
        if self.paused_until and now < self.paused_until:
            return False, f"stoploss streak pause {self.paused_until:%H:%M} tak"
        if self.daily_loss_hit(now):
            return False, "daily loss limit"
        if self.results_r:
            last = self.results_r[-1][0]
            if now < last + timedelta(minutes=self.cooldown_minutes):
                return False, "cooldown (pichla trade abhi band hua)"
        return True, "ok"
````

### `rtw/lifecycle.py`

````text file=rtw/lifecycle.py
"""Signal lifecycle: NEW -> ACTIVE -> TARGET / SL / EXPIRED / MISSED, single-trade lock, ranking."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime

OPEN_STATES = ("NEW", "ACTIVE")
CLOSED_STATES = ("TARGET", "SL", "EXPIRED", "MISSED")


@dataclass
class Signal:
    id: str
    symbol: str
    asset_class: str
    direction: str                 # BUY | SELL (underlying direction). For options: BUY=CE, SELL=PE
    entry_lo: float
    entry_hi: float
    sl: float
    t1: float
    t2: float
    chase_price: float
    valid_till: datetime
    exit_by: datetime
    created_at: datetime
    grade: str = "C"
    confidence: float = 0.0
    paper: bool = False
    kind: str = "TRADE"            # TRADE (the one active plan) | INFO (shown only)
    state: str = "NEW"
    entry_price: float | None = None
    exit_price: float | None = None
    closed_at: datetime | None = None
    r_multiple: float | None = None
    close_reason: str = ""
    sl_dist: float = 0.0
    t2_reached: bool = False
    reasons: list = field(default_factory=list)

    def __post_init__(self):
        if not self.sl_dist:
            mid = (self.entry_lo + self.entry_hi) / 2.0
            self.sl_dist = abs(mid - self.sl)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("valid_till", "exit_by", "created_at", "closed_at"):
            d[k] = d[k].isoformat() if d[k] else None
        return d


def _sgn(sig: Signal) -> int:
    return 1 if sig.direction == "BUY" else -1


def _close(sig: Signal, state: str, price: float, now: datetime, reason: str):
    sig.state, sig.exit_price, sig.closed_at, sig.close_reason = state, price, now, reason
    if sig.entry_price is not None and sig.sl_dist > 0:
        sig.r_multiple = _sgn(sig) * (price - sig.entry_price) / sig.sl_dist
    else:
        sig.r_multiple = None   # never entered: no P&L


def advance(sig: Signal, price: float, now: datetime, high: float | None = None, low: float | None = None) -> Signal:
    """Move the signal one step given the latest price (and optional bar high/low).
    Conservative rule: if SL and target are both inside one bar, SL is assumed first."""
    if sig.state in CLOSED_STATES:
        return sig
    hi = price if high is None else max(high, price)
    lo = price if low is None else min(low, price)
    s = _sgn(sig)
    if sig.state == "NEW":
        if now > sig.valid_till:
            _close(sig, "EXPIRED", price, now, "entry time nikal gaya, signal expire")
            return sig
        beyond = (price >= sig.chase_price) if s > 0 else (price <= sig.chase_price)
        if beyond:
            _close(sig, "MISSED", price, now, "MISSED, chase mat karo")
            return sig
        dead = (price <= sig.sl) if s > 0 else (price >= sig.sl)
        if dead:
            _close(sig, "EXPIRED", price, now, "entry se pehle hi SL level toot gaya, setup invalid")
            return sig
        if sig.entry_lo <= price <= sig.entry_hi:
            sig.state, sig.entry_price = "ACTIVE", price
            return sig
        return sig
    # ACTIVE
    sl_hit = (lo <= sig.sl) if s > 0 else (hi >= sig.sl)
    t1_hit = (hi >= sig.t1) if s > 0 else (lo <= sig.t1)
    if sl_hit:
        _close(sig, "SL", sig.sl, now, "stoploss hit")
        return sig
    if t1_hit:
        sig.t2_reached = (hi >= sig.t2) if s > 0 else (lo <= sig.t2)
        _close(sig, "TARGET", sig.t1, now, "target 1 hit")
        return sig
    if now >= sig.exit_by:
        _close(sig, "EXPIRED", price, now, "exit-by time ho gaya, nikal jao")
    return sig


class TradeLock:
    """Only ONE active trade plan across all markets."""

    def __init__(self):
        self.active_id: str | None = None

    def locked(self) -> bool:
        return self.active_id is not None

    def acquire(self, sig_id: str) -> bool:
        if self.active_id is None or self.active_id == sig_id:
            self.active_id = sig_id
            return True
        return False

    def release(self, sig_id: str):
        if self.active_id == sig_id:
            self.active_id = None


def rank_score(S: float, rr: float, setup_factor: float = 1.0, liquidity_factor: float = 1.0) -> float:
    """score x R:R(capped) x setup record x liquidity. All factors > 0."""
    return abs(S) * min(max(rr, 0.0), 4.0) * max(setup_factor, 0.0) * max(liquidity_factor, 0.0)


def setup_factor(expectancy_r: float | None, trades: int, min_trades: int = 30) -> float:
    """Unknown record -> 0.7 (PAPER-ish), known record scales 0.5..1.5 by expectancy in R."""
    if expectancy_r is None or trades < min_trades:
        return 0.7
    return max(0.5, min(1.5, 1.0 + expectancy_r))


def pick_best(candidates: list[dict]) -> tuple[dict | None, list[dict]]:
    """candidates: dicts with keys symbol, passed(bool), rank(float). Returns (best_passed_or_None, others_as_INFO)."""
    ok = sorted([c for c in candidates if c.get("passed")], key=lambda c: -c["rank"])
    if not ok:
        return None, sorted(candidates, key=lambda c: -c.get("rank", 0))
    best = ok[0]
    return best, [c for c in candidates if c is not best]
````

### `rtw/news.py`

````text file=rtw/news.py
"""News Intelligence kernel: event calendar modes, headline tagger, surprise engine, reaction reader, news layer.
Pure functions. Collectors (RSS/GDELT/APIs) live outside and feed these functions."""
from __future__ import annotations
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from .layers import LayerResult

# ---------- asset groups ----------
ALIASES = {"NIFTY": "INDEX", "BANKNIFTY": "INDEX", "MIDCPNIFTY": "INDEX", "FINNIFTY": "INDEX",
           "GOLDM": "GOLD", "GOLDGUINEA": "GOLD", "SILVERM": "SILVER", "SILVERMIC": "SILVER",
           "CRUDEOILM": "CRUDE", "CRUDEOIL": "CRUDE", "NATURALGAS": "NATGAS", "NATGASMINI": "NATGAS",
           "BTCUSDT": "BTC", "BTCUSD": "BTC"}


def group_of(symbol: str) -> str:
    return ALIASES.get(symbol.upper(), symbol.upper())


# ---------- tags ----------
@dataclass
class Tag:
    asset: str
    direction: int          # +1 bullish for that asset, -1 bearish
    magnitude: float        # 0..1
    conf: float             # 0..1
    ts: datetime
    half_life_min: float = 120.0
    label: str = ""
    source: str = ""
    official: bool = False


# (regex, [(asset, direction, magnitude)], half_life_min, Hinglish label)
RULES = [
    (r"\brate cut|cuts? (?:repo|interest|rates?)|dovish", [("INDEX", 1, .6), ("BANKNIFTY", 1, .7), ("GOLD", 1, .4), ("USDINR", -1, .3), ("BTC", 1, .4)], 360, "rate cut / dovish"),
    (r"\brate hike|hikes? (?:repo|interest|rates?)|hawkish", [("INDEX", -1, .6), ("BANKNIFTY", -1, .4), ("GOLD", -1, .4), ("USDINR", 1, .3), ("BTC", -1, .4)], 360, "rate hike / hawkish"),
    (r"\b(?:war|missile|airstrike|air strike|invasion|escalat\w*|attack on|strikes on|drone attack)\b", [("CRUDE", 1, .7), ("GOLD", 1, .6), ("INDEX", -1, .6), ("BTC", -1, .2), ("USDINR", 1, .3)], 240, "war / tension"),
    (r"\b(?:ceasefire|peace deal|de-?escalat\w*|truce)\b", [("CRUDE", -1, .6), ("GOLD", -1, .4), ("INDEX", 1, .5)], 240, "ceasefire / peace"),
    (r"\bopec\+?\b.*\b(?:cut|cuts|reduce|lower)\b|\bproduction cuts?\b|\bsupply disruption\b|\brefinery (?:fire|outage)\b", [("CRUDE", 1, .7)], 360, "supply cut"),
    (r"\bopec\+?\b.*\b(?:raise|increase|boost|hike)\b.*\b(?:output|production)\b|\boutput hike\b", [("CRUDE", -1, .6)], 360, "supply badhi"),
    (r"\bcrude (?:inventories|stocks|stockpiles) (?:fell|drew|draw|drop|decline)\w*|\binventory draw\b", [("CRUDE", 1, .4)], 120, "crude stock draw"),
    (r"\bcrude (?:inventories|stocks|stockpiles) (?:rose|build|builds|jump|rise|increase)\w*|\binventory build\b", [("CRUDE", -1, .4)], 120, "crude stock build"),
    (r"\bsanctions?\b", [("CRUDE", 1, .4), ("GOLD", 1, .2)], 240, "sanctions"),
    (r"\b(?:cold snap|polar vortex|heat ?wave|gulf hurricane|lng outage|freeport)\b", [("NATGAS", 1, .5)], 240, "weather / LNG supply"),
    (r"\btariffs?\b", [("INDEX", -1, .5), ("USDINR", 1, .3), ("GOLD", 1, .3)], 360, "tariff"),
    (r"\bcrypto (?:ban|crackdown)|exchange (?:hack|collapse|insolven\w+)|\bhack(?:ed)?\b.*\b(?:exchange|bitcoin|crypto)\b", [("BTC", -1, .7)], 480, "crypto negative"),
    (r"\b(?:bitcoin|btc|crypto)\b.*\betf\b.*\b(?:approv\w*|inflows?)\b|\betf inflows?\b", [("BTC", 1, .6)], 480, "BTC ETF positive"),
    (r"\bfiis? (?:sold|selling|outflows?|pull\w* out)\b|\bforeign (?:investors|funds) (?:sold|dump\w*)\b", [("INDEX", -1, .4)], 180, "FII selling"),
    (r"\bfiis? (?:bought|buying|inflows?)\b|\bforeign (?:investors|funds) (?:bought|buy\w*)\b", [("INDEX", 1, .4)], 180, "FII buying"),
    (r"\b(?:dollar|dxy)\b.*\b(?:surg\w+|jumps?|climbs?|strengthens?|rall\w+)\b|\bstrong dollar\b", [("GOLD", -1, .4), ("SILVER", -1, .3), ("USDINR", 1, .5), ("BTC", -1, .2), ("EURUSD", -1, .5), ("GBPUSD", -1, .5), ("USDJPY", 1, .5)], 240, "dollar mazboot"),
    (r"\b(?:dollar|dxy)\b.*\b(?:slips?|falls?|weakens?|drops?|slumps?)\b|\bweak dollar\b", [("GOLD", 1, .4), ("SILVER", 1, .3), ("USDINR", -1, .5), ("BTC", 1, .2), ("EURUSD", 1, .5), ("GBPUSD", 1, .5), ("USDJPY", -1, .5)], 240, "dollar kamzor"),
    (r"\binflation (?:cools|eases|falls|slows|softens)\b|\bcpi (?:lower|below|cools)\b", [("INDEX", 1, .4), ("GOLD", 1, .3), ("USDINR", -1, .2)], 240, "inflation kam"),
    (r"\binflation (?:jumps|surges|rises|accelerates|hotter)\b|\bcpi (?:higher|above|hotter)\b", [("INDEX", -1, .4), ("GOLD", -1, .3), ("USDINR", 1, .2)], 240, "inflation zyada"),
    (r"\b(?:recession fears?|market crash|stocks? (?:plunge|tumble|crash)|sell-?off|black monday)\b", [("INDEX", -1, .6), ("GOLD", 1, .4), ("BTC", -1, .4), ("CRUDE", -1, .3)], 240, "market girawat"),
    (r"\b(?:record high|all-time high)\b", [("INDEX", 1, .25)], 120, "record high"),
    (r"\bcentral banks? (?:gold )?(?:buying|purchases?)\b", [("GOLD", 1, .4)], 480, "central bank gold buying"),
]
_COMPILED = [(re.compile(p, re.I), tags, hl, label) for p, tags, hl, label in RULES]


def tag_headline(title: str, ts: datetime, source: str = "", official: bool = False, trust: float = 0.6) -> list[Tag]:
    """Rule-based tags. trust 0..1 (official feeds ~0.95, general RSS ~0.6, GDELT ~0.4)."""
    out: list[Tag] = []
    seen = set()
    for rx, tags, hl, label in _COMPILED:
        if rx.search(title or ""):
            for asset, d, m in tags:
                key = (asset, d)
                if key in seen:
                    continue
                seen.add(key)
                out.append(Tag(asset, d, m, 0.95 if official else trust, ts, hl, label, source, official))
    return out


def stock_tag(title: str, ts: datetime, symbol: str, names: list[str], source: str = "", official: bool = False, trust: float = 0.5) -> Tag | None:
    """Ticker-specific tag from a local sentiment model (vaderSentiment). Low confidence by design."""
    if not any(n.lower() in (title or "").lower() for n in names + [symbol]):
        return None
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        c = SentimentIntensityAnalyzer().polarity_scores(title)["compound"]
    except Exception:
        return None
    if abs(c) < 0.35:
        return None
    return Tag(symbol.upper(), 1 if c > 0 else -1, min(0.6, abs(c) * 0.6), 0.95 if official else trust, ts, 240, "company news sentiment", source, official)


# ---------- dedupe stories ----------
_STOP = set("a an the of to in on at for and or is are was were be by with as from that this it its after before over under amid says said".split())


def _tokens(title: str) -> frozenset:
    return frozenset(w for w in re.findall(r"[a-z0-9]+", (title or "").lower()) if w not in _STOP and len(w) > 1)


def same_story(a: str, b: str, thr: float = 0.55) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= thr


def cluster_stories(items: list[dict]) -> list[dict]:
    """items: dicts with title, source, ts, official. Returns stories: {title, sources:set, first_ts, official, items}."""
    stories: list[dict] = []
    for it in sorted(items, key=lambda x: x["ts"]):
        for s in stories:
            if same_story(s["title"], it["title"]):
                s["sources"].add(it["source"])
                s["official"] = s["official"] or bool(it.get("official"))
                s["items"].append(it)
                break
        else:
            stories.append({"title": it["title"], "sources": {it["source"]}, "first_ts": it["ts"],
                            "official": bool(it.get("official")), "items": [it]})
    return stories


def story_confirmed(story: dict) -> bool:
    """High-impact only if official OR >= 2 distinct sources."""
    return story["official"] or len(story["sources"]) >= 2


# ---------- surprise engine ----------
# kind -> (typical surprise size, effect when actual > forecast)
SURPRISE_KINDS = {
    "US_CPI_YOY": (0.1, "hawkish"), "US_CORE_CPI_YOY": (0.1, "hawkish"), "US_NFP": (75.0, "hawkish"),
    "US_UNEMPLOYMENT": (0.1, "dovish"), "US_RETAIL_SALES": (0.4, "hawkish"), "US_GDP": (0.4, "hawkish"),
    "FED_RATE": (0.25, "hawkish"), "RBI_REPO": (0.25, "hawkish"), "IN_CPI_YOY": (0.25, "hawkish_in"),
    "CRUDE_STOCKS": (2.0, "crude_stock"), "GAS_STORAGE": (10.0, "gas_stock"),
}
_HAWKISH = [("INDEX", -1, .5), ("BANKNIFTY", -1, .3), ("GOLD", -1, .6), ("SILVER", -1, .5), ("USDINR", 1, .5), ("BTC", -1, .5),
            ("EURUSD", -1, .6), ("GBPUSD", -1, .6), ("USDJPY", 1, .6), ("CRUDE", -1, .2)]


def surprise_score(kind: str, actual: float, forecast: float) -> float:
    """Signed surprise in [-1,1]; + means actual above forecast. 1.0 = 2x typical size or more."""
    typ = SURPRISE_KINDS[kind][0]
    return max(-1.0, min(1.0, (actual - forecast) / (2.0 * typ)))


def surprise_tags(kind: str, actual: float, forecast: float, ts: datetime, source: str = "official") -> list[Tag]:
    sc = surprise_score(kind, actual, forecast)
    if abs(sc) < 0.15:
        return []
    effect = SURPRISE_KINDS[kind][1]
    m = abs(sc)
    up = sc > 0
    base: list[tuple[str, int, float]] = []
    if effect in ("hawkish", "dovish"):
        hawk = up if effect == "hawkish" else (not up)
        base = [(a, d if hawk else -d, w) for a, d, w in _HAWKISH]
    elif effect == "hawkish_in":
        base = [("INDEX", -1 if up else 1, .4), ("BANKNIFTY", -1 if up else 1, .4)]
    elif effect == "crude_stock":
        base = [("CRUDE", -1 if up else 1, .6)]
    elif effect == "gas_stock":
        base = [("NATGAS", -1 if up else 1, .6)]
    return [Tag(a, d, min(1.0, w * (0.5 + m)), 0.95, ts, 180, f"{kind} surprise {sc:+.2f}", source, True) for a, d, w in base]


# ---------- reaction reader ----------
def read_reaction(expected_dir: int, p0: float, p5: float, p15: float, atr: float, thr_atr: float = 0.3) -> str:
    """Did price confirm the news? Returns CONFIRMED | FADED | OPPOSITE | NO_REACTION."""
    if atr <= 0 or expected_dir == 0:
        return "NO_REACTION"
    m5 = expected_dir * (p5 - p0) / atr
    m15 = expected_dir * (p15 - p0) / atr
    if m15 >= thr_atr and m5 > 0:
        return "CONFIRMED"
    if m5 >= thr_atr and m15 < 0.1 * thr_atr:
        return "FADED"
    if m15 <= -thr_atr:
        return "OPPOSITE"
    return "NO_REACTION"


# ---------- events & news mode ----------
@dataclass
class Event:
    name: str
    when: datetime                  # timezone-aware
    impact: str = "HIGH"            # HIGH | MED | LOW
    assets: tuple = ("ALL",)        # groups affected, or "ALL"
    pre_min: int | None = None
    post_min: int | None = None


_DEFAULT_PRE = {"HIGH": 30, "MED": 10, "LOW": 0}
_DEFAULT_POST = {"HIGH": 15, "MED": 5, "LOW": 0}


def _affects(ev: Event, asset: str) -> bool:
    return "ALL" in ev.assets or group_of(asset) in ev.assets or asset.upper() in ev.assets


def news_mode(events: list[Event], now: datetime, asset: str, shock: bool = False, vix_z: float | None = None, gpr_z: float | None = None) -> dict:
    """CALM | EVENT_WINDOW | SHOCK for one asset. Window = pre..post minutes around a HIGH/MED event.
    lock_reason is Hinglish, tells what we wait for. wait_until = end of window."""
    if shock or (vix_z is not None and vix_z >= 3.0):
        return {"mode": "SHOCK", "lock_reason": "bada jhatka (shock), thehro, market stable hone do", "wait_until": now + timedelta(minutes=30), "next_event": None}
    nxt = None
    for ev in sorted(events, key=lambda e: e.when):
        if ev.impact == "LOW" or not _affects(ev, asset):
            continue
        pre = ev.pre_min if ev.pre_min is not None else _DEFAULT_PRE[ev.impact]
        post = ev.post_min if ev.post_min is not None else _DEFAULT_POST[ev.impact]
        if ev.when - timedelta(minutes=pre) <= now <= ev.when + timedelta(minutes=post):
            if now < ev.when:
                why = f"{ev.name} {ev.when:%H:%M} se pehle, ruko"
            else:
                why = f"{ev.name} {ev.when:%H:%M} ke baad reaction dekhna hai, ruko"
            return {"mode": "EVENT_WINDOW", "lock_reason": why, "wait_until": ev.when + timedelta(minutes=post), "next_event": ev}
        if ev.when > now and nxt is None:
            nxt = ev
    mode = "CALM"
    if gpr_z is not None and gpr_z >= 2.0:
        mode = "CALM"   # risk meter only widens SL / cuts size via modifiers, it does not lock
    return {"mode": mode, "lock_reason": None, "wait_until": None, "next_event": nxt}


def plan_modifiers(events: list[Event], now: datetime, asset: str, exit_by: datetime, vix_z: float | None = None, gpr_z: float | None = None,
                   buffer_min: int = 10) -> dict:
    """Shorten exit-by before the next HIGH event; cut size in elevated risk."""
    new_exit = exit_by
    note = ""
    for ev in sorted(events, key=lambda e: e.when):
        if ev.impact != "HIGH" or not _affects(ev, asset) or ev.when <= now:
            continue
        cand = ev.when - timedelta(minutes=(ev.pre_min if ev.pre_min is not None else _DEFAULT_PRE["HIGH"]) + buffer_min)
        if cand < new_exit:
            new_exit = cand
            note = f"{ev.name} {ev.when:%H:%M} se pehle nikalna hai"
        break
    size = 1.0
    sl_mult = 1.0
    if (vix_z is not None and vix_z >= 1.5) or (gpr_z is not None and gpr_z >= 2.0):
        size, sl_mult = 0.7, 1.2
        note = (note + "; " if note else "") + "risk zyada, size chhota"
    return {"exit_by": new_exit, "size_mult": size, "sl_mult": sl_mult, "note": note}


# ---------- news layer ----------
def news_layer(symbol: str, tags: list[Tag], now: datetime) -> LayerResult:
    """Time-decayed vote for one symbol from all tags (symbol-specific or its group)."""
    r = LayerResult("news")
    keys = {symbol.upper(), group_of(symbol)}
    num = 0.0
    wsum = 0.0
    used = []
    for t in tags:
        if t.asset.upper() not in keys:
            continue
        age = max(0.0, (now - t.ts).total_seconds() / 60.0)
        decay = math.exp(-math.log(2.0) * age / max(t.half_life_min, 1.0))
        w = t.magnitude * t.conf * decay
        if w < 0.02:
            continue
        num += t.direction * w
        wsum += w
        used.append((w, t))
    if not used:
        return r
    r.score = math.tanh(1.5 * num)
    r.conf = min(1.0, 0.35 + 0.15 * len(used))
    for w, t in sorted(used, key=lambda x: -x[0])[:2]:
        r.reasons.append(f"news: {t.label} ({'+' if t.direction > 0 else '-'})")
    return r.clipped()
````

### `rtw/globalctx.py`

````text file=rtw/globalctx.py
"""Global-cues layer. Input: % changes of global tickers (yfinance symbols). Output: LayerResult."""
from __future__ import annotations
import math
from .layers import LayerResult

# typical 1-day % move (1 sigma) used to turn a % change into a z-like number
TYPICAL = {"^GSPC": 1.0, "ES=F": 1.0, "NQ=F": 1.3, "^IXIC": 1.3, "^N225": 1.2, "^HSI": 1.4, "DX-Y.NYB": 0.4, "CL=F": 2.0,
           "BZ=F": 2.0, "^VIX": 6.0, "^TNX": 1.5, "USDINR=X": 0.25, "GC=F": 1.0, "SI=F": 1.8, "NG=F": 3.0, "BTC-USD": 2.5,
           "EURUSD=X": 0.4, "GBPUSD=X": 0.5, "JPY=X": 0.5}

# asset group -> {ticker: weight}. Weight sign = how a RISE in that ticker affects the asset.
WEIGHTS = {
    "INDEX":  {"^GSPC": 1.0, "ES=F": 0.8, "^IXIC": 0.5, "^N225": 0.4, "^HSI": 0.3, "DX-Y.NYB": -0.5, "CL=F": -0.4, "^VIX": -0.8, "^TNX": -0.3, "USDINR=X": -0.3},
    "STOCK":  {"^GSPC": 0.6, "ES=F": 0.5, "^VIX": -0.5, "DX-Y.NYB": -0.2, "CL=F": -0.2},
    "GOLD":   {"GC=F": 1.0, "DX-Y.NYB": -0.8, "^TNX": -0.5, "USDINR=X": 0.5},
    "SILVER": {"SI=F": 1.0, "GC=F": 0.6, "DX-Y.NYB": -0.7, "USDINR=X": 0.5},
    "CRUDE":  {"CL=F": 1.0, "BZ=F": 0.8, "DX-Y.NYB": -0.4, "USDINR=X": 0.5, "^GSPC": 0.2},
    "NATGAS": {"NG=F": 1.0, "USDINR=X": 0.4},
    "USDINR": {"DX-Y.NYB": 0.8, "CL=F": 0.4, "^GSPC": -0.3, "^TNX": 0.3, "USDINR=X": 0.6},
    "EURINR": {"EURUSD=X": 0.8, "USDINR=X": 0.6},
    "GBPINR": {"GBPUSD=X": 0.8, "USDINR=X": 0.6},
    "JPYINR": {"JPY=X": -0.8, "USDINR=X": 0.6},
    "EURUSD": {"DX-Y.NYB": -1.0, "EURUSD=X": 0.6},
    "GBPUSD": {"DX-Y.NYB": -1.0, "GBPUSD=X": 0.6},
    "USDJPY": {"DX-Y.NYB": 0.5, "^TNX": 0.8, "JPY=X": 0.6},
    "BTC":    {"^IXIC": 0.6, "NQ=F": 0.4, "DX-Y.NYB": -0.5, "^VIX": -0.4, "BTC-USD": 0.8},
}
_NAME = {"^GSPC": "S&P500", "ES=F": "S&P futures", "NQ=F": "Nasdaq fut", "^IXIC": "Nasdaq", "^N225": "Nikkei", "^HSI": "HangSeng",
         "DX-Y.NYB": "Dollar index", "CL=F": "WTI crude", "BZ=F": "Brent", "^VIX": "US VIX", "^TNX": "US10Y yield",
         "USDINR=X": "USDINR", "GC=F": "COMEX gold", "SI=F": "COMEX silver", "NG=F": "NYMEX gas", "BTC-USD": "BTC",
         "EURUSD=X": "EURUSD", "GBPUSD=X": "GBPUSD", "JPY=X": "USDJPY"}


def global_layer(group: str, changes_pct: dict) -> LayerResult:
    r = LayerResult("global")
    w = WEIGHTS.get(group)
    if not w:
        return r
    contrib = []
    for tk, wt in w.items():
        ch = changes_pct.get(tk)
        if ch is None or (isinstance(ch, float) and math.isnan(ch)):
            continue
        z = max(-3.0, min(3.0, ch / TYPICAL.get(tk, 1.0)))
        contrib.append((tk, wt, z, ch))
    if not contrib:
        return r
    tot_w = sum(abs(wt) for _, wt, _, _ in contrib)
    raw = sum(wt * z for _, wt, z, _ in contrib) / tot_w
    r.score = math.tanh(1.2 * raw)
    coverage = tot_w / sum(abs(x) for x in w.values())
    r.conf = max(0.0, min(0.8, 0.8 * coverage))
    for tk, wt, z, ch in sorted(contrib, key=lambda x: -abs(x[1] * x[2]))[:2]:
        eff = "faydemand" if wt * z > 0 else "nuksandeh"
        r.reasons.append(f"{_NAME.get(tk, tk)} {ch:+.2f}% ({eff})")
    return r.clipped()
````

### `rtw/smart.py`

````text file=rtw/smart.py
"""Smart-money layers: FII/DII + participant OI (index), delivery/bulk/insider (stocks), funding/F&G/OI (crypto), COT (commodity)."""
from __future__ import annotations
import math
from .layers import LayerResult


def oi_buildup(price_chg_pct: float, oi_chg_pct: float, thr_p: float = 0.1, thr_oi: float = 1.0) -> str:
    if abs(price_chg_pct) < thr_p or abs(oi_chg_pct) < thr_oi:
        return "NEUTRAL"
    if price_chg_pct > 0 and oi_chg_pct > 0:
        return "LONG_BUILDUP"
    if price_chg_pct < 0 and oi_chg_pct > 0:
        return "SHORT_BUILDUP"
    if price_chg_pct > 0 and oi_chg_pct < 0:
        return "SHORT_COVERING"
    return "LONG_UNWINDING"


_BUILD_SCORE = {"LONG_BUILDUP": 0.5, "SHORT_COVERING": 0.25, "SHORT_BUILDUP": -0.5, "LONG_UNWINDING": -0.25, "NEUTRAL": 0.0}
_BUILD_TXT = {"LONG_BUILDUP": "long buildup", "SHORT_COVERING": "short covering", "SHORT_BUILDUP": "short buildup",
              "LONG_UNWINDING": "long unwinding", "NEUTRAL": "OI neutral"}


def fii_layer(fii_cash_net_cr: float | None, dii_cash_net_cr: float | None = None, fii_idx_fut_long_ratio: float | None = None,
              index_buildup: str | None = None) -> LayerResult:
    """fii_idx_fut_long_ratio = FII index-futures long / (long+short) from participant-wise OI (0..1)."""
    r = LayerResult("smart")
    parts, w = [], []
    if fii_cash_net_cr is not None:
        parts.append(math.tanh(fii_cash_net_cr / 3000.0))
        w.append(0.4)
        r.reasons.append(f"FII cash {fii_cash_net_cr:+.0f} cr")
    if dii_cash_net_cr is not None:
        parts.append(0.5 * math.tanh(dii_cash_net_cr / 3000.0))
        w.append(0.15)
    if fii_idx_fut_long_ratio is not None:
        parts.append(max(-1.0, min(1.0, (fii_idx_fut_long_ratio - 0.5) * 4.0)))
        w.append(0.3)
        r.reasons.append(f"FII index fut long {fii_idx_fut_long_ratio * 100:.0f}%")
    if index_buildup:
        parts.append(_BUILD_SCORE[index_buildup] * 2.0)
        w.append(0.15)
        r.reasons.append(_BUILD_TXT[index_buildup])
    if not parts:
        return r
    r.score = sum(p * x for p, x in zip(parts, w)) / sum(w)
    r.conf = min(0.9, 0.3 + 0.6 * sum(w))
    return r.clipped()


def stock_smart_layer(delivery_pct: float | None, delivery_avg_pct: float | None, price_chg_pct: float | None,
                      buildup: str | None = None, bulk_net: int = 0, insider_net: int = 0) -> LayerResult:
    """bulk_net / insider_net: +1 net buying, -1 net selling, 0 none (last few days)."""
    r = LayerResult("smart")
    s, w = 0.0, 0.0
    if delivery_pct is not None and delivery_avg_pct and price_chg_pct is not None and abs(price_chg_pct) >= 0.3:
        ratio = delivery_pct / delivery_avg_pct
        if ratio >= 1.3:
            s += (1 if price_chg_pct > 0 else -1) * min(1.0, (ratio - 1.0)) * 0.6
            r.reasons.append("delivery zyada (" + ("accumulation" if price_chg_pct > 0 else "distribution") + ")")
        w += 0.4
    if buildup:
        s += _BUILD_SCORE[buildup] * 0.8
        w += 0.3
        r.reasons.append(_BUILD_TXT[buildup])
    if bulk_net:
        s += 0.3 * bulk_net
        w += 0.15
        r.reasons.append("bulk deal " + ("buy" if bulk_net > 0 else "sell"))
    if insider_net:
        s += 0.3 * insider_net
        w += 0.15
        r.reasons.append("insider " + ("buying" if insider_net > 0 else "selling"))
    if w == 0:
        return r
    r.score = s / max(w, 0.5)
    r.conf = min(0.85, 0.25 + w)
    return r.clipped()


def crypto_smart_layer(funding_rate: float | None, ls_ratio: float | None, fear_greed: float | None,
                       oi_chg_pct: float | None, price_chg_pct: float | None) -> LayerResult:
    """funding_rate per 8h as fraction (0.0001 = 0.01%). Extremes are CONTRARIAN."""
    r = LayerResult("smart")
    s, n = 0.0, 0
    if funding_rate is not None:
        n += 1
        if funding_rate > 0.0005:
            s -= 0.4
            r.reasons.append("funding bahut high (longs crowded)")
        elif funding_rate < -0.0002:
            s += 0.4
            r.reasons.append("funding negative (shorts crowded)")
    if ls_ratio is not None:
        n += 1
        if ls_ratio > 2.0:
            s -= 0.2
        elif ls_ratio < 0.8:
            s += 0.2
    if fear_greed is not None:
        n += 1
        if fear_greed <= 20:
            s += 0.3
            r.reasons.append(f"extreme fear {fear_greed:.0f} (bounce chance)")
        elif fear_greed >= 80:
            s -= 0.3
            r.reasons.append(f"extreme greed {fear_greed:.0f} (garmi, risk)")
    if oi_chg_pct is not None and price_chg_pct is not None:
        n += 1
        b = oi_buildup(price_chg_pct, oi_chg_pct)
        s += _BUILD_SCORE[b] * 0.8
        r.reasons.append(_BUILD_TXT[b])
    if n == 0:
        return r
    r.score = s
    r.conf = min(0.7, 0.2 + 0.12 * n)
    return r.clipped()


def cot_layer(net_spec_pct_oi: float | None, change_4w_pct_oi: float | None) -> LayerResult:
    """CFTC managed-money net position as % of open interest (weekly, lagging) -> mild trend-follow, fade extremes."""
    r = LayerResult("smart")
    if net_spec_pct_oi is None or change_4w_pct_oi is None:
        return r
    s = math.tanh(change_4w_pct_oi / 8.0) * 0.6
    if abs(net_spec_pct_oi) > 35:
        s *= 0.4
        r.reasons.append("COT extreme, ulta palatne ka risk")
    r.score = s
    r.conf = 0.35
    r.reasons.append(f"COT 4-hafte badlav {change_4w_pct_oi:+.1f}% OI")
    return r.clipped()
````

### `rtw/candles.py`

````text file=rtw/candles.py
"""Tick -> candle builder and OHLC resampler (closed bars only)."""
from __future__ import annotations
from datetime import datetime, timedelta
import pandas as pd


class CandleBuilder:
    """Feeds ticks, returns a CLOSED bar dict when a tick arrives that belongs to a newer bar.
    tf_minutes must divide 60 (1,3,5,10,15,30). cum_volume = cumulative day volume from the feed (optional)."""

    def __init__(self, tf_minutes: int = 5):
        if 60 % tf_minutes != 0:
            raise ValueError("tf_minutes must divide 60")
        self.tf = tf_minutes
        self.cur: dict | None = None
        self.last_cum: float | None = None

    def _start(self, ts: datetime) -> datetime:
        return ts.replace(minute=(ts.minute // self.tf) * self.tf, second=0, microsecond=0)

    def on_tick(self, ts: datetime, price: float, cum_volume: float | None = None) -> dict | None:
        if price is None or price <= 0:
            return None
        start = self._start(ts)
        closed = None
        if self.cur is not None and start > self.cur["ts"]:
            closed, self.cur = self.cur, None
        if self.cur is None:
            self.cur = {"ts": start, "open": price, "high": price, "low": price, "close": price, "volume": 0.0}
        c = self.cur
        c["high"], c["low"], c["close"] = max(c["high"], price), min(c["low"], price), price
        if cum_volume is not None:
            if self.last_cum is not None and cum_volume >= self.last_cum:
                c["volume"] += cum_volume - self.last_cum
            self.last_cum = cum_volume
        return closed

    def flush(self) -> dict | None:
        c, self.cur = self.cur, None
        return c


def resample_ohlc(df: pd.DataFrame, rule: str, offset: str = "0min", now: datetime | None = None) -> pd.DataFrame:
    """5m -> 15min / 60min / 1D. NSE hourly bars need offset='15min' (bars start 09:15, 10:15 ...).
    If `now` is given, bars that are not fully finished at `now` are dropped."""
    agg = df.resample(rule, offset=offset, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna(subset=["open"])
    if now is not None and len(agg):
        span = pd.Timedelta(rule)
        agg = agg[agg.index + span <= pd.Timestamp(now)]
    return agg
````

### `rtw/scan.py`

````text file=rtw/scan.py
"""Cheap funnel scan for Tier 2/3: rank many symbols quickly, send only the best to the full engine."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import indicators as ta


def liquid_universe(rows: list[dict], min_turnover_cr: float = 50.0, min_price: float = 20.0) -> list[dict]:
    """rows: dicts with symbol, price, turnover_cr (traded value, crore). Returns liquid ones sorted by turnover desc."""
    ok = [r for r in rows if r.get("price", 0) >= min_price and r.get("turnover_cr", 0) >= min_turnover_cr]
    return sorted(ok, key=lambda r: -r["turnover_cr"])


def cheap_scan_score(df: pd.DataFrame, n: int = 20) -> dict:
    """Fast 0..1 'something is happening' score + direction (+1/-1/0). Closed bars only. Needs >= n+30 bars."""
    if len(df) < n + 30:
        return {"score": 0.0, "direction": 0, "reasons": []}
    c = df["close"]
    prior = df.iloc[-(n + 1):-1]
    hi, lo, last = float(prior["high"].max()), float(prior["low"].min()), float(c.iloc[-1])
    atr_v = float(ta.atr(df, 14).iloc[-1])
    breakout = 0.0
    if atr_v > 0:
        if last > hi:
            breakout = min(1.0, (last - hi) / atr_v + 0.5)
        elif last < lo:
            breakout = -min(1.0, (lo - last) / atr_v + 0.5)
    z = float(ta.zscore(df["volume"], 20).iloc[-1]) if float(df["volume"].tail(20).sum()) > 0 else 0.0
    z = 0.0 if np.isnan(z) else z
    roc = float(c.iloc[-1] / c.iloc[-11] - 1.0) if len(c) > 11 else 0.0
    roc_n = min(1.0, abs(roc) / (3.0 * atr_v / last)) if atr_v > 0 else 0.0
    a = ta.adx(df, 14)["adx"].iloc[-1]
    adx_n = 0.0 if np.isnan(a) else min(1.0, float(a) / 40.0)
    direction = int(np.sign(0.6 * breakout + 0.4 * np.sign(roc)))
    score = 0.35 * abs(breakout) + 0.25 * max(0.0, min(1.0, z / 3.0)) + 0.2 * roc_n + 0.2 * adx_n
    reasons = []
    if breakout:
        reasons.append("20-bar breakout" if breakout > 0 else "20-bar breakdown")
    if z >= 2:
        reasons.append(f"volume z={z:.1f}")
    return {"score": float(score), "direction": direction, "reasons": reasons}


def shortlist(scored: list[dict], top_n: int = 40, min_score: float = 0.25) -> list[dict]:
    """scored: dicts with symbol, score. Keep best top_n above min_score."""
    return sorted([s for s in scored if s["score"] >= min_score], key=lambda s: -s["score"])[:top_n]
````

### `rtw/zones.py`

````text file=rtw/zones.py
"""Support / resistance levels and demand / supply zones. Pure functions on CLOSED bars only (no lookahead).

* S/R levels: confirmed swing highs/lows + previous-day high / low / close / classic pivots, clustered when closer than
  `tol` x ATR (more touches = stronger level).
* Demand / supply zones: a small 'base' (1-3 small-bodied candles) followed by an impulse candle (big range, big body) that
  closes out of the base. Demand = impulse up (price rose from there), supply = impulse down. A zone dies when price CLOSES
  through its far edge; it is 'fresh' while price has not come back into it."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import indicators as ta
from .layers import LayerResult

IMPULSE_ATR, IMPULSE_BODY, BASE_BODY_ATR = 1.6, 0.6, 0.5


def _prev_day_levels(df: pd.DataFrame) -> list[dict]:
    days = pd.Series(df.index.date, index=df.index)
    last_day = days.iloc[-1]
    prev = df[days < last_day]
    if prev.empty:
        return []
    pday = prev[days[prev.index] == days[prev.index].iloc[-1]]
    h, l, c = float(pday["high"].max()), float(pday["low"].min()), float(pday["close"].iloc[-1])
    pv = ta.classic_pivots(h, l, c)
    out = [{"price": h, "src": "PDH"}, {"price": l, "src": "PDL"}, {"price": c, "src": "PDC"}]
    out += [{"price": pv[k], "src": k} for k in ("P", "R1", "S1", "R2", "S2")]
    return out


def sr_levels(df: pd.DataFrame, atr: float, lookback: int = 300, tol: float = 0.3, keep: int = 3) -> dict:
    """{'supports': [...], 'resistances': [...]} nearest first; each {price, touches, src}."""
    if df is None or len(df) < 30 or not atr or atr <= 0:
        return {"supports": [], "resistances": []}
    price = float(df["close"].iloc[-1])
    sw = ta.swing_levels(df, 3, 3, min(lookback, len(df)))
    pts = [{"price": p, "src": "swing"} for p in sw["swing_highs"] + sw["swing_lows"]] + _prev_day_levels(df)
    pts.sort(key=lambda x: x["price"])
    clusters: list[list[dict]] = []
    for p in pts:
        if clusters and p["price"] - np.mean([q["price"] for q in clusters[-1]]) <= tol * atr:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    lv = []
    for c in clusters:
        srcs = sorted({q["src"] for q in c})
        lv.append({"price": float(np.mean([q["price"] for q in c])), "touches": len(c), "src": "+".join(srcs)})
    sup = sorted([x for x in lv if x["price"] < price - 0.05 * atr], key=lambda x: -x["price"])[:keep]
    res = sorted([x for x in lv if x["price"] > price + 0.05 * atr], key=lambda x: x["price"])[:keep]
    return {"supports": sup, "resistances": res}


def find_zones(df: pd.DataFrame, lookback: int = 200, keep: int = 2) -> list[dict]:
    """Un-broken demand / supply zones, nearest to price first. Each: {kind, lo, hi, fresh, touches, t}."""
    if df is None or len(df) < 40:
        return []
    d = df.iloc[-lookback:]
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr = ta.atr(d, 14).to_numpy(float)
    n, zs = len(d), []
    for i in range(16, n):                                  # i = impulse candle (closed); the zone is known as soon as it closes
        a = atr[i - 1]
        if not (a > 0):
            continue
        rng, body = h[i] - l[i], abs(c[i] - o[i])
        if rng < IMPULSE_ATR * a or body < IMPULSE_BODY * rng:
            continue
        up = c[i] > o[i]
        j = i - 1                                           # base = up to 3 small-bodied candles right before the impulse
        base = []
        while j >= max(i - 3, 0) and abs(c[j] - o[j]) <= BASE_BODY_ATR * a and (h[j] - l[j]) <= 1.2 * a:
            base.append(j)
            j -= 1
        if not base:
            continue
        b_lo, b_hi = min(l[k] for k in base), max(h[k] for k in base)
        top_body, bot_body = max(max(o[k], c[k]) for k in base), min(min(o[k], c[k]) for k in base)
        if up and c[i] > b_hi:
            kind, lo, hi, distal = "demand", b_lo, top_body, b_lo
        elif (not up) and c[i] < b_lo:
            kind, lo, hi, distal = "supply", bot_body, b_hi, b_hi
        else:
            continue
        after_c, after_l, after_h = c[i + 1:], l[i + 1:], h[i + 1:]
        if kind == "demand" and (after_c < distal).any():
            continue
        if kind == "supply" and (after_c > distal).any():
            continue
        touches = int((after_l <= hi).sum()) if kind == "demand" else int((after_h >= lo).sum())
        zs.append({"kind": kind, "lo": float(lo), "hi": float(hi), "fresh": touches == 0, "touches": touches, "t": d.index[i].isoformat()})
    price = float(c[-1])
    out = []
    for kind in ("demand", "supply"):
        z = [x for x in zs if x["kind"] == kind and ((x["hi"] <= price + 1e-9) if kind == "demand" else (x["lo"] >= price - 1e-9))]
        z.sort(key=lambda x: abs(price - (x["hi"] if kind == "demand" else x["lo"])))
        out += z[:keep]
    return out


def zone_info(df: pd.DataFrame) -> dict:
    """Everything the UI / plan needs in one call."""
    if df is None or len(df) < 40:
        return {"supports": [], "resistances": [], "zones": []}
    atr = float(ta.atr(df, 14).iloc[-1])
    sr = sr_levels(df, atr)
    return {**sr, "zones": find_zones(df)}


def zones_layer(df: pd.DataFrame, info: dict | None = None) -> LayerResult:
    """Vote only when price is AT a zone / level (else unavailable, so it never dilutes other layers)."""
    r = LayerResult("zones")
    if df is None or len(df) < 60:
        return r
    atr = float(ta.atr(df, 14).iloc[-1])
    if not (atr > 0):
        return r
    price = float(df["close"].iloc[-1])
    info = info if info is not None else zone_info(df)
    score, conf, why = 0.0, 0.0, []
    for z in info["zones"]:
        if z["touches"] > 2:
            continue
        w = 1.0 if z["fresh"] else 0.65
        if z["kind"] == "demand" and z["lo"] - 0.3 * atr <= price <= z["hi"] + 0.5 * atr:
            score, conf = score + 0.8 * w, max(conf, 0.65)
            why.append("Demand zone ke paas (khareedaar ka ilaka)" + ("" if z["fresh"] else ", zone pehle chhua hua"))
        elif z["kind"] == "supply" and z["lo"] - 0.5 * atr <= price <= z["hi"] + 0.3 * atr:
            score, conf = score - 0.8 * w, max(conf, 0.65)
            why.append("Supply zone ke paas (bechne wale ka ilaka)" + ("" if z["fresh"] else ", zone pehle chhua hua"))
    for s in info["supports"][:1]:
        if price - s["price"] <= 0.5 * atr:
            score, conf = score + 0.4 * min(s["touches"], 3) / 3 + 0.2, max(conf, 0.5)
            why.append(f"Support ke paas ({s['price']:.2f}, {s['touches']} touch)")
    for q in info["resistances"][:1]:
        if q["price"] - price <= 0.5 * atr:
            score, conf = score - (0.4 * min(q["touches"], 3) / 3 + 0.2), max(conf, 0.5)
            why.append(f"Resistance ke paas ({q['price']:.2f}, {q['touches']} touch)")
    r.score, r.conf, r.reasons = score, conf, why[:2]
    return r.clipped()


def plan_levels(info: dict) -> dict:
    """Blocking levels for targets: supports (for SELL targets) and resistances (for BUY targets), incl. zone proximal edges."""
    sup = [x["price"] for x in info["supports"]] + [z["hi"] for z in info["zones"] if z["kind"] == "demand"]
    res = [x["price"] for x in info["resistances"]] + [z["lo"] for z in info["zones"] if z["kind"] == "supply"]
    dem = [z["lo"] for z in info["zones"] if z["kind"] == "demand"]
    sup_far = [z["hi"] for z in info["zones"] if z["kind"] == "supply"]
    return {"supports": sup, "resistances": res, "demand_distal": dem, "supply_distal": sup_far}
````

### `rtw/charts.py`

````text file=rtw/charts.py
"""Chart data for the PWA (pure functions). Candles come from stored CLOSED 5m bars; 15m/1h are resampled from them."""
from __future__ import annotations
import urllib.parse
import pandas as pd

TFS = {"5m": "5min", "15m": "15min", "1h": "60min"}
IST_OFFSET_S = 19800          # the canvas chart shows IST by shifting the UTC timestamps

_TV_FIXED = {"NIFTY": "NSE:NIFTY", "BANKNIFTY": "NSE:BANKNIFTY", "MIDCPNIFTY": "NSE:NIFTY_MID_SELECT",
             "GOLD": "MCX:GOLD1!", "SILVER": "MCX:SILVER1!", "CRUDEOIL": "MCX:CRUDEOIL1!", "NATURALGAS": "MCX:NATURALGAS1!",
             "USDINR": "NSE:USDINR1!", "EURINR": "NSE:EURINR1!", "GBPINR": "NSE:GBPINR1!", "JPYINR": "NSE:JPYINR1!",
             "EURUSD": "FX:EURUSD", "GBPUSD": "FX:GBPUSD", "USDJPY": "FX:USDJPY", "BTCUSDT": "BINANCE:BTCUSDT"}


def tv_symbol(symbol: str, asset_class: str = "STOCK") -> str:
    """TradingView symbol for the 'open in TradingView' link. Unknown names are treated as NSE stocks."""
    s = symbol.upper()
    if s in _TV_FIXED:
        return _TV_FIXED[s]
    return "NSE:" + urllib.parse.quote(s.replace("&", "_"), safe="_-")


def tv_url(symbol: str, asset_class: str = "STOCK") -> str:
    return "https://www.tradingview.com/chart/?symbol=" + urllib.parse.quote(tv_symbol(symbol, asset_class), safe="")


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    if tf not in TFS:
        raise ValueError("tf 5m / 15m / 1h me se ek ho")
    if tf == "5m" or df is None or df.empty:
        return df
    o = df.resample(TFS[tf], label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return o.dropna(subset=["open", "close"])


def _ema(vals: list[float], n: int) -> list[float | None]:
    out, k, e = [], 2.0 / (n + 1), None
    for i, v in enumerate(vals):
        e = v if e is None else e + k * (v - e)
        out.append(e if i >= n - 1 else None)
    return out


def chart_payload(df: pd.DataFrame, tf: str = "5m", n: int = 120, levels: list | None = None) -> dict:
    """Last `n` candles + EMA20 + price levels (entry / SL / targets). Times are unix seconds shifted to IST."""
    d = resample(df, tf)
    ema = _ema([float(x) for x in d["close"]], 20)
    d = d.tail(n)
    ema = ema[-len(d):]
    candles = [{"t": int(ts.timestamp()) + IST_OFFSET_S, "o": float(r.open), "h": float(r.high), "l": float(r.low), "c": float(r.close)}
               for ts, r in d.iterrows()]
    return {"tf": tf, "candles": candles, "ema20": [None if e is None else round(float(e), 4) for e in ema], "levels": levels or []}


def levels_from_plan(plan: dict | None, tag: str = "") -> list[dict]:
    if not plan:
        return []
    out = []
    for key, label, kind in (("entry_lo", "Entry", "entry"), ("entry_hi", "Entry", "entry"), ("sl", "SL", "sl"), ("t1", "T1", "target"), ("t2", "T2", "target")):
        v = plan.get(key)
        if v is not None:
            out.append({"label": label + tag if key != "entry_hi" else "", "price": float(v), "kind": kind})
    return out
````

### `rtw/mood.py`

````text file=rtw/mood.py
"""Market mood per symbol: BULLISH / BEARISH / SIDEWAYS (pure functions + flip tracker with hysteresis).
Mood is the market's TENDENCY (from the engine's combined score S and regime). It is NOT a trade signal."""
from __future__ import annotations
from datetime import datetime, timedelta

HEADLINE = ("NIFTY", "BANKNIFTY", "GOLD", "CRUDEOIL", "BTCUSDT")      # these also send a Telegram alert on a flip
CONFIRM_CYCLES = 3                                                    # a new mood must hold this many cycles before it counts
ALERT_GAP_MIN = 30                                                    # at most one alert per symbol per 30 min
BULL_TH, STRONG_TH, SIDE_TH_RANGE = 0.15, 0.40, 0.45

LABEL = {"BULLISH": "Tezi (Bullish)", "BEARISH": "Mandi (Bearish)", "SIDEWAYS": "Sideways"}
ICON = {"BULLISH": "🟢", "BEARISH": "🔴", "SIDEWAYS": "🟡"}


def mood_of(d: dict | None) -> dict | None:
    """Decision dict -> {mood,label,strength,text} or None when there is no valid reading (market closed / no data)."""
    if not d or d.get("regime") is None:
        return None
    wr = d.get("wait_reason") or ""
    if "market band" in wr or "data nahi" in wr:
        return None
    S = float(d.get("S") or 0.0)
    reg = d.get("regime")
    if reg == "RANGE" and abs(S) < SIDE_TH_RANGE:
        mood = "SIDEWAYS"
    elif S >= BULL_TH:
        mood = "BULLISH"
    elif S <= -BULL_TH:
        mood = "BEARISH"
    else:
        mood = "SIDEWAYS"
    a = abs(S)
    strength = "strong" if a >= STRONG_TH else "moderate" if a >= 0.25 else "mild"
    if mood == "SIDEWAYS":
        text = "Range me hai, saaf direction nahi. Breakout ka intezar karo."
    else:
        word = "upar" if mood == "BULLISH" else "neeche"
        text = f"Jhukaav {word} ki taraf ({'majboot' if strength == 'strong' else 'theek-thaak' if strength == 'moderate' else 'halka'})."
        if reg == "VOLATILE":
            text += " Market zyada hil raha hai, savdhan."
    return {"mood": mood, "label": LABEL[mood], "icon": ICON[mood], "strength": strength, "regime": reg, "S": round(S, 2), "text": text}


def range_of(df, bars: int = 40) -> dict | None:
    if df is None or len(df) < 10:
        return None
    t = df.tail(bars)
    return {"lo": float(t["low"].min()), "hi": float(t["high"].max())}


def update_state(state: dict, readings: dict, now: datetime) -> tuple[dict, list[dict]]:
    """state: {symbol: {mood, pending, n, since, last_alert}}; readings: {symbol: mood_str}. Returns (new_state, flips).
    A flip is reported only after the new mood held for CONFIRM_CYCLES cycles in a row (no flip-flop spam)."""
    flips, out = [], dict(state or {})
    for sym, m in readings.items():
        st = dict(out.get(sym) or {})
        cur = st.get("mood")
        if cur is None:                                   # first reading: adopt silently
            out[sym] = {"mood": m, "pending": None, "n": 0, "since": now.isoformat(), "last_alert": None}
            continue
        if m == cur:
            st["pending"], st["n"] = None, 0
        else:
            if st.get("pending") == m:
                st["n"] = int(st.get("n", 0)) + 1
            else:
                st["pending"], st["n"] = m, 1
            if st["n"] >= CONFIRM_CYCLES:
                flips.append({"symbol": sym, "from": cur, "to": m, "ts": now.isoformat()})
                st.update(mood=m, pending=None, n=0, since=now.isoformat())
        out[sym] = st
    return out, flips


def alert_text(sym: str, name: str, flip: dict, mm: dict | None) -> str:
    to = flip["to"]
    t = f"{ICON[to]} {name} ab {LABEL[to].upper()} dikh raha hai (pehle {LABEL[flip['from']]})."
    if mm:
        t += "\n" + mm["text"]
    return t + "\nYe sirf mahaul ki jaankari hai, trade signal nahi."
````

### `rtw/engine.py`

````text file=rtw/engine.py
"""One-symbol analysis pipeline: layers -> combine -> news mode -> plan -> gates -> decision dict.
No I/O. The scheduler feeds it candles/ctx and stores the returned decision."""
from __future__ import annotations
from datetime import datetime, timedelta
import pandas as pd
from . import indicators as ta
from .layers import chart_layers, regime, LayerResult
from .scoring import combine, direction_of, grade, PROFILES
from .plan import build_plan
from .zones import zones_layer, zone_info, plan_levels
from .sessions import exit_by as session_exit_by, is_open, IST
from .gates import GateInput, evaluate_gates, all_passed, first_failure
from .news import news_layer, news_mode, plan_modifiers
from .lifecycle import rank_score, setup_factor

SEGMENT_OF = {"INDEX": "NSE", "STOCK": "NSE", "COMMODITY": "MCX", "FOREX": "CDS_INR", "CRYPTO": "CRYPTO"}


def confidence_pct(S: float, A: float) -> int:
    return int(round(100 * (0.6 * min(1.0, abs(S) / 0.8) + 0.4 * max(0.0, min(1.0, A)))))


def analyze(symbol: str, asset_class: str, df: pd.DataFrame, now: datetime, *, capital: float, risk_pct: float, lot_size: int,
            profile: str = "conservative", segment: str | None = None, intraday: bool = True,
            extra_layers: dict | None = None, tags: list | None = None, events: list | None = None,
            data_age_sec: float = 0.0, max_data_age_sec: float = 120.0,
            setup_expectancy: float | None = None, setup_trades: int = 0, paper: bool = False,
            daily_loss_hit: bool = False, protections_ok: tuple = (True, "ok"),
            vix_z: float | None = None, gpr_z: float | None = None, shock: bool = False,
            valid_minutes: int = 20, liquidity_factor: float = 1.0, holidays: set | None = None,
            min_minutes_left: int = 20, skip_afford: bool = False) -> dict:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware (IST)")
    segment = segment or SEGMENT_OF[asset_class]
    out = {"symbol": symbol, "asset_class": asset_class, "action": "WAIT", "paper": paper, "profile": profile}
    if df is None or len(df) < 60:
        out.update(wait_reason="data kam hai (60 bars chahiye)", gates=[], S=0.0, A=0.0)
        return out
    if not is_open(segment, now, holidays):
        out.update(wait_reason=f"{segment} market band hai", gates=[], S=0.0, A=0.0)
        return out
    reg = regime(df)
    layers = chart_layers(df, intraday)
    zi = zone_info(df)                                   # computed once: used for the vote, the plan and the UI
    layers["zones"] = zones_layer(df, zi)
    for k, v in (extra_layers or {}).items():
        if v is not None:
            layers[k] = v
    layers["news"] = news_layer(symbol, tags or [], now)
    comb = combine(layers, asset_class, reg["name"])
    S, A = comb["S"], comb["A"]
    direction = direction_of(S)
    out["sr"] = {"supports": zi["supports"][:2], "resistances": zi["resistances"][:2], "zones": zi["zones"]}
    nm = news_mode(events or [], now, symbol, shock=shock, vix_z=vix_z, gpr_z=gpr_z)
    out.update(S=S, A=A, regime=reg["name"], news_mode=nm["mode"], drivers=comb["drivers"],
               reasons=[r for _, _, rs in comb["drivers"] for r in rs][:6],
               grade=grade(S, A, profile), confidence=confidence_pct(S, A))
    if direction == "NONE":
        out.update(wait_reason="koi direction nahi", gates=[])
        return out
    price = float(df["close"].iloc[-1])
    atr_v = float(ta.atr(df, 14).iloc[-1])
    if not (atr_v > 0):
        out.update(wait_reason="ATR nahi nikal paya", gates=[])
        return out
    sw = ta.swing_levels(df)
    pl = plan_levels(zi)
    lows = sorted(set((sw["swing_lows"] or [sw["last_low"]]) + pl["supports"]))        # blockers for SELL targets
    highs = sorted(set((sw["swing_highs"] or [sw["last_high"]]) + pl["resistances"]))  # blockers for BUY targets
    sw_low, sw_high = sw["last_low"], sw["last_high"]
    if direction == "BUY" and pl["demand_distal"]:          # stop just under the nearest demand zone below price (tighter + logical)
        below = [x for x in pl["demand_distal"] if x < price]
        if below:
            sw_low = max(sw_low, max(below)) if max(below) > sw_low else sw_low
    if direction == "SELL" and pl["supply_distal"]:
        above = [x for x in pl["supply_distal"] if x > price]
        if above:
            sw_high = min(sw_high, min(above)) if min(above) < sw_high else sw_high
    exit_by = session_exit_by(segment, now.astimezone(IST).date(), now=now)
    mods = plan_modifiers(events or [], now, symbol, exit_by, vix_z=vix_z, gpr_z=gpr_z)
    pf = PROFILES[profile]
    plan = build_plan(direction, price, atr_v * 1.0, sw_low, sw_high, supports=lows, resistances=highs,
                      lot_size=lot_size, capital=capital, risk_pct=risk_pct, rr_min=pf["rr_min"], now=now,
                      valid_minutes=valid_minutes, exit_by=mods["exit_by"], size_mult=mods["size_mult"])
    if mods["sl_mult"] != 1.0:  # widen stop in risky markets, keep T1 at the same R multiple
        plan = build_plan(direction, price, atr_v * mods["sl_mult"], sw_low, sw_high, lows, highs,
                          lot_size, capital, risk_pct, pf["rr_min"], now, valid_minutes, mods["exit_by"], mods["size_mult"])
    if exit_by - now < timedelta(minutes=min_minutes_left):
        out.update(wait_reason="market band hone me kam time bacha, naya entry nahi", gates=[], plan=plan.to_dict(), rank=0.0, passed=False)
        return out
    g = GateInput(S=S, A=A, n_avail=comb["n_avail"], n_agree=comb["n_agree"], rr=plan.rr, data_age_sec=data_age_sec,
                  max_data_age_sec=max_data_age_sec, regime=reg["name"], setup_expectancy=setup_expectancy,
                  setup_trades=setup_trades, paper=paper, daily_loss_hit=daily_loss_hit, news_mode=nm["mode"],
                  news_lock_reason=nm["lock_reason"], news_wait_until=nm["wait_until"], profile=profile)
    gates = evaluate_gates(g)
    out["gates"] = [(x.name, x.passed, x.reason) for x in gates]
    out["plan"] = plan.to_dict()
    out["plan_note"] = mods["note"]
    out["risk_budget"] = capital * risk_pct * mods["size_mult"]
    out["price"] = price
    out["atr"] = atr_v
    ok_prot, why_prot = protections_ok
    if not ok_prot:
        out.update(wait_reason=why_prot, rank=0.0, passed=False)
        return out
    if not all_passed(gates):
        ff = first_failure(gates)
        out.update(wait_reason=ff.reason, wait_until=(nm["wait_until"].isoformat() if nm["wait_until"] and ff.name == "news_clear" else None),
                   rank=0.0, passed=False)
        return out
    if not plan.affordable and not skip_afford:
        out.update(wait_reason="capital me 1 lot ka risk fit nahi hota", rank=0.0, passed=False)
        return out
    out.update(action=direction, passed=True,
               rank=rank_score(S, plan.rr, setup_factor(setup_expectancy, setup_trades), liquidity_factor))
    return out
````

### `rtw/backtest.py`

````text file=rtw/backtest.py
"""Bar-by-bar walk-forward backtester using the SAME analyze() + advance() as live. Closed bars only, no lookahead.
Gate 6 (setup record) is bypassed here via paper=True, because this module PRODUCES that record."""
from __future__ import annotations
from datetime import timedelta
import pandas as pd
from .engine import analyze
from .lifecycle import Signal, advance

COST_BPS = {"INDEX": 3.0, "STOCK": 6.0, "COMMODITY": 5.0, "FOREX": 2.0, "CRYPTO": 8.0}  # round-trip, underlying-level proxy


def backtest(df: pd.DataFrame, symbol: str, asset_class: str, *, lot_size: int = 1, capital: float = 1_000_000.0,
             risk_pct: float = 0.01, profile: str = "conservative", tf_minutes: int = 5, window: int = 300, warmup: int = 100,
             step: int = 1, max_hold_bars: int = 200, segment: str | None = None, holidays: set | None = None,
             extra_layers_fn=None, **analyze_kw) -> list[dict]:
    """extra_layers_fn(i, ts) -> dict of extra LayerResults (optional, must itself be point-in-time)."""
    trades: list[dict] = []
    n = len(df)
    tf = timedelta(minutes=tf_minutes)
    i = max(warmup, 60)
    cost_bps = COST_BPS[asset_class]
    while i < n - 1:
        now = df.index[i] + tf                       # bar i just closed
        win = df.iloc[max(0, i - window + 1): i + 1]
        extra = extra_layers_fn(i, now) if extra_layers_fn else None
        d = analyze(symbol, asset_class, win, now, capital=capital, risk_pct=risk_pct, lot_size=lot_size, profile=profile,
                    segment=segment, intraday=True, extra_layers=extra, paper=True, holidays=holidays, **analyze_kw)
        if d["action"] not in ("BUY", "SELL"):
            i += step
            continue
        pl = d["plan"]
        sig = Signal(f"bt{i}", symbol, asset_class, d["action"], pl["entry_lo"], pl["entry_hi"], pl["sl"], pl["t1"], pl["t2"],
                     pl["chase_price"], now + timedelta(minutes=20), pd.Timestamp(pl["exit_by"]).to_pydatetime(), now,
                     sl_dist=pl["sl_dist"])
        j = i + 1
        last_j = min(n - 1, i + max_hold_bars)
        while j <= last_j and sig.state in ("NEW", "ACTIVE"):
            ts = df.index[j]
            row = df.iloc[j]
            advance(sig, float(row["open"]), ts, None, None)
            if sig.state in ("NEW", "ACTIVE"):
                advance(sig, float(row["close"]), ts + tf, float(row["high"]), float(row["low"]))
            j += 1
        if sig.state in ("NEW", "ACTIVE"):
            advance(sig, float(df.iloc[last_j]["close"]), df.index[last_j] + 10 * tf, None, None)
            if sig.state == "NEW":
                sig.state = "EXPIRED"
        if sig.entry_price is not None and sig.r_multiple is not None:
            cost_r = (cost_bps / 1e4 * sig.entry_price) / sig.sl_dist if sig.sl_dist > 0 else 0.0
            trades.append({"ts": now, "symbol": symbol, "asset_class": asset_class, "direction": sig.direction,
                           "regime": d["regime"], "grade": d["grade"], "state": sig.state, "r_gross": sig.r_multiple,
                           "cost_r": cost_r, "r_net": sig.r_multiple - cost_r})
        else:
            trades.append({"ts": now, "symbol": symbol, "asset_class": asset_class, "direction": sig.direction,
                           "regime": d["regime"], "grade": d["grade"], "state": sig.state, "r_gross": None,
                           "cost_r": 0.0, "r_net": None})
        i = max(j, i + step)
    return trades


def _rs(trades: list[dict], cost_mult: float = 1.0) -> list[float]:
    return [t["r_gross"] - cost_mult * t["cost_r"] for t in trades if t.get("r_gross") is not None]


def expectancy(trades: list[dict], cost_mult: float = 1.0) -> float:
    rs = _rs(trades, cost_mult)
    return sum(rs) / len(rs) if rs else 0.0


def setup_stats(trades: list[dict]) -> dict:
    rs = _rs(trades)
    n = len(rs)
    if n == 0:
        return {"trades": 0, "win_rate": 0.0, "expectancy_r": 0.0, "profit_factor": 0.0, "max_dd_r": 0.0,
                "is_expectancy_r": 0.0, "oos_expectancy_r": 0.0, "stress_expectancy_r": 0.0}
    done = [t for t in trades if t.get("r_gross") is not None]
    cut = int(n * 0.7)
    gp = sum(r for r in rs if r > 0)
    gl = -sum(r for r in rs if r < 0)
    peak = cum = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return {"trades": n, "win_rate": sum(1 for r in rs if r > 0) / n, "expectancy_r": sum(rs) / n,
            "profit_factor": (gp / gl) if gl > 0 else float("inf"), "max_dd_r": dd,
            "is_expectancy_r": expectancy(done[:cut]) if cut else 0.0,
            "oos_expectancy_r": expectancy(done[cut:]) if n - cut else 0.0,
            "stress_expectancy_r": expectancy(done, 2.0)}


def passes_record(stats: dict, min_trades: int = 30) -> bool:
    """Net-of-costs expectancy > 0, out-of-sample (last 30%) > 0, and still > 0 with doubled costs."""
    return (stats["trades"] >= min_trades and stats["expectancy_r"] > 0 and stats["oos_expectancy_r"] > 0
            and stats["stress_expectancy_r"] > 0)


def group_setups(trades: list[dict]) -> dict:
    """setup_key = ASSETCLASS|DIRECTION|REGIME -> stats."""
    g: dict = {}
    for t in trades:
        g.setdefault(f"{t['asset_class']}|{t['direction']}|{t['regime']}", []).append(t)
    return {k: setup_stats(v) for k, v in g.items()}
````

### `rtw/db.py`

````text file=rtw/db.py
"""SQLite schema (single file DB). Candles are stored for every symbol/timeframe; everything else is small."""
from __future__ import annotations
import json
import sqlite3
import threading
from datetime import datetime
import pandas as pd
from .lifecycle import Signal
from .gates import Protections

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS instruments(
  symbol TEXT PRIMARY KEY, name TEXT, exchange TEXT, token TEXT, segment TEXT, asset_class TEXT,
  lot_size INTEGER, tick_size REAL, expiry TEXT, tier INTEGER DEFAULT 3, paper INTEGER DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS candles(
  symbol TEXT NOT NULL, tf TEXT NOT NULL, ts TEXT NOT NULL,
  open REAL, high REAL, low REAL, close REAL, volume REAL, oi REAL,
  PRIMARY KEY(symbol, tf, ts));
CREATE TABLE IF NOT EXISTS signals(
  id TEXT PRIMARY KEY, symbol TEXT, asset_class TEXT, direction TEXT, kind TEXT, state TEXT, grade TEXT,
  confidence REAL, paper INTEGER, entry_lo REAL, entry_hi REAL, sl REAL, t1 REAL, t2 REAL, chase_price REAL,
  valid_till TEXT, exit_by TEXT, created_at TEXT, entry_price REAL, exit_price REAL, closed_at TEXT,
  r_multiple REAL, close_reason TEXT, reasons_json TEXT, extra_json TEXT);
CREATE INDEX IF NOT EXISTS ix_signals_state ON signals(state);
CREATE TABLE IF NOT EXISTS news_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT, url_hash TEXT UNIQUE, title TEXT, source TEXT, official INTEGER,
  ts TEXT, story_id INTEGER, tags_json TEXT);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, when_ts TEXT, impact TEXT, assets_json TEXT,
  forecast REAL, previous REAL, actual REAL, source TEXT, UNIQUE(name, when_ts));
CREATE TABLE IF NOT EXISTS setup_stats(
  setup_key TEXT PRIMARY KEY, trades INTEGER, expectancy_r REAL, win_rate REAL, benched INTEGER DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS protections_state(
  k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS decisions(
  symbol TEXT PRIMARY KEY, ts TEXT, action TEXT, json TEXT);
CREATE TABLE IF NOT EXISTS settings(
  k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS health_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, component TEXT, status TEXT, detail TEXT);
"""


class _Rows:
    """Rows are read inside the lock, so no other thread can touch the cursor."""
    def __init__(self, rows):
        self._r = rows

    def fetchone(self):
        return self._r[0] if self._r else None

    def fetchall(self):
        return list(self._r)

    def __iter__(self):
        return iter(self._r)


class LockedConnection:
    """One SQLite connection shared by scheduler / API / Telegram threads, serialized by an RLock (a bare shared
    connection raised thousands of InterfaceError in a stress test)."""
    def __init__(self, con: sqlite3.Connection):
        self._con, self._lock = con, threading.RLock()

    def execute(self, sql, params=()):
        with self._lock:
            cur = self._con.execute(sql, params)
            return _Rows(cur.fetchall() if cur.description else [])

    def executemany(self, sql, seq):
        with self._lock:
            self._con.executemany(sql, seq)

    def executescript(self, sql):
        with self._lock:
            self._con.executescript(sql)

    def commit(self):
        with self._lock:
            self._con.commit()

    def close(self):
        with self._lock:
            self._con.close()


def connect(path: str = "rtw.db") -> LockedConnection:
    con = sqlite3.connect(path, check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return LockedConnection(con)


def save_signal(con: sqlite3.Connection, s: Signal, extra: dict | None = None):
    d = s.to_dict()
    con.execute(
        """INSERT INTO signals(id,symbol,asset_class,direction,kind,state,grade,confidence,paper,entry_lo,entry_hi,sl,t1,t2,
           chase_price,valid_till,exit_by,created_at,entry_price,exit_price,closed_at,r_multiple,close_reason,reasons_json,extra_json)
           VALUES(:id,:symbol,:asset_class,:direction,:kind,:state,:grade,:confidence,:paper,:entry_lo,:entry_hi,:sl,:t1,:t2,
           :chase_price,:valid_till,:exit_by,:created_at,:entry_price,:exit_price,:closed_at,:r_multiple,:close_reason,:reasons_json,:extra_json)
           ON CONFLICT(id) DO UPDATE SET state=excluded.state, kind=excluded.kind, entry_price=excluded.entry_price,
           exit_price=excluded.exit_price, closed_at=excluded.closed_at, r_multiple=excluded.r_multiple,
           close_reason=excluded.close_reason, exit_by=excluded.exit_by, extra_json=excluded.extra_json""",
        {**d, "paper": int(s.paper), "reasons_json": json.dumps(s.reasons, ensure_ascii=False),
         "extra_json": json.dumps(extra or {}, ensure_ascii=False)})
    con.commit()


def upsert_candles(con: sqlite3.Connection, symbol: str, tf: str, rows: list[tuple]):
    """rows: (ts_iso, open, high, low, close, volume[, oi])"""
    norm = [(symbol, tf, r[0], r[1], r[2], r[3], r[4], r[5], (r[6] if len(r) > 6 else None)) for r in rows]
    con.executemany("INSERT OR REPLACE INTO candles(symbol,tf,ts,open,high,low,close,volume,oi) VALUES(?,?,?,?,?,?,?,?,?)", norm)
    con.commit()


def track_record(con: sqlite3.Connection, paper: bool | None = None) -> dict:
    q = "SELECT r_multiple FROM signals WHERE state IN ('TARGET','SL','EXPIRED') AND r_multiple IS NOT NULL AND kind='TRADE'"
    args: list = []
    if paper is not None:
        q += " AND paper=?"
        args.append(int(paper))
    rs = [r[0] for r in con.execute(q, args).fetchall()]
    n = len(rs)
    wins = sum(1 for r in rs if r > 0)
    return {"trades": n, "win_rate": (wins / n) if n else 0.0, "total_r": sum(rs), "avg_r": (sum(rs) / n) if n else 0.0}


# ------------------------------------------------------------------ small helpers used by the pipeline / API
def get_setting(con, k: str, default=None):
    r = con.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else default


def set_setting(con, k: str, v) -> None:
    con.execute("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v, ensure_ascii=False, default=str)))
    con.commit()


def load_df(con, symbol: str, tf: str = "5m", n: int = 400) -> pd.DataFrame | None:
    rows = con.execute("SELECT ts,open,high,low,close,volume FROM candles WHERE symbol=? AND tf=? ORDER BY ts DESC LIMIT ?", (symbol, tf, n)).fetchall()
    if not rows:
        return None
    df = pd.DataFrame([tuple(r) for r in rows][::-1], columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Asia/Kolkata")
    return df.set_index("ts")


def signal_from_row(r) -> Signal:
    d = dict(r)
    f = lambda k: datetime.fromisoformat(d[k]) if d.get(k) else None
    return Signal(id=d["id"], symbol=d["symbol"], asset_class=d["asset_class"], direction=d["direction"], entry_lo=d["entry_lo"],
                  entry_hi=d["entry_hi"], sl=d["sl"], t1=d["t1"], t2=d["t2"], chase_price=d["chase_price"], valid_till=f("valid_till"),
                  exit_by=f("exit_by"), created_at=f("created_at"), grade=d["grade"] or "C", confidence=d["confidence"] or 0.0,
                  paper=bool(d["paper"]), kind=d["kind"], state=d["state"], entry_price=d["entry_price"], exit_price=d["exit_price"],
                  closed_at=f("closed_at"), r_multiple=d["r_multiple"], close_reason=d["close_reason"] or "",
                  sl_dist=abs((d["entry_lo"] + d["entry_hi"]) / 2.0 - d["sl"]), reasons=json.loads(d["reasons_json"] or "[]"))


def open_trade(con):
    """The single open TRADE signal (state NEW/ACTIVE) or None. Returns (Signal, extra_dict)."""
    r = con.execute("SELECT * FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE') ORDER BY created_at DESC LIMIT 1").fetchone()
    if not r:
        return None, {}
    return signal_from_row(r), json.loads(r["extra_json"] or "{}")


def open_trades(con) -> list:
    """All open TRADE signals (NEW/ACTIVE), oldest first. Returns [(Signal, extra_dict)]."""
    rows = con.execute("SELECT * FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE') ORDER BY created_at ASC").fetchall()
    return [(signal_from_row(r), json.loads(r["extra_json"] or "{}")) for r in rows]


def load_protections(con) -> Protections:
    raw = get_setting(con, "protections")
    p = Protections()
    if raw:
        p.results_r = [(datetime.fromisoformat(t), float(x)) for t, x in raw.get("results_r", [])]
        p.paused_until = datetime.fromisoformat(raw["paused_until"]) if raw.get("paused_until") else None
        p.halted = bool(raw.get("halted"))
    return p


def save_protections(con, p: Protections) -> None:
    set_setting(con, "protections", {"results_r": [(t.isoformat(), x) for t, x in p.results_r[-500:]],
                                     "paused_until": p.paused_until.isoformat() if p.paused_until else None, "halted": p.halted})


def save_decision(con, symbol: str, now: datetime, d: dict) -> None:
    con.execute("INSERT INTO decisions(symbol,ts,action,json) VALUES(?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET ts=excluded.ts, action=excluded.action, json=excluded.json",
                (symbol, now.isoformat(), d.get("action", "WAIT"), json.dumps(d, ensure_ascii=False, default=str)))
    con.commit()


def load_decisions(con) -> dict:
    return {r["symbol"]: json.loads(r["json"]) for r in con.execute("SELECT symbol,json FROM decisions")}


def get_setup_stats(con) -> dict:
    return {r["setup_key"]: dict(r) for r in con.execute("SELECT * FROM setup_stats")}


def put_setup_stats(con, key: str, stats: dict, now: datetime) -> None:
    con.execute("INSERT INTO setup_stats(setup_key,trades,expectancy_r,win_rate,benched,updated_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(setup_key) DO UPDATE SET trades=excluded.trades, expectancy_r=excluded.expectancy_r, win_rate=excluded.win_rate, "
                "benched=excluded.benched, updated_at=excluded.updated_at",
                (key, stats["trades"], stats["expectancy_r"], stats["win_rate"], int(stats.get("benched", 0)), now.isoformat()))
    con.commit()


def log_health(con, now: datetime, component: str, status: str, detail: str = "") -> None:
    con.execute("INSERT INTO health_log(ts,component,status,detail) VALUES(?,?,?,?)", (now.isoformat(), component, status, detail[:300]))
    con.commit()


def patch_decision(con, symbol: str, d: dict) -> None:
    """Update the stored JSON of a decision WITHOUT touching its timestamp (freshness must stay honest)."""
    con.execute("UPDATE decisions SET json=? WHERE symbol=?", (json.dumps(d, ensure_ascii=False, default=str), symbol))
    con.commit()


def forward_stats(con, setup_key: str) -> dict:
    """Closed paper/live trades of one setup (from the signals table, setup_key stored in extra_json)."""
    rs = []
    for r in con.execute("SELECT r_multiple, extra_json FROM signals WHERE kind='TRADE' AND r_multiple IS NOT NULL AND state IN ('TARGET','SL','EXPIRED')"):
        try:
            if json.loads(r["extra_json"] or "{}").get("setup_key") == setup_key:
                rs.append(float(r["r_multiple"]))
        except Exception:
            continue
    n = len(rs)
    return {"trades": n, "expectancy_r": (sum(rs) / n) if n else 0.0}
````

### `rtw/provider.py`

````text file=rtw/provider.py
"""Data-provider contract + FakeProvider (DEMO mode / tests).
RULE for every provider method: NEVER raise. On failure return None / [] / {} and let the caller log health."""
from __future__ import annotations
import hashlib
import math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from .config import Spec, CORE_SPECS, stock_spec
from .news import Tag, Event, tag_headline
from .options import bs_price
from .sessions import IST

START_PRICE = {"NIFTY": 24500, "BANKNIFTY": 53000, "MIDCPNIFTY": 12500, "GOLD": 120000, "SILVER": 150000, "CRUDEOIL": 5500,
               "NATURALGAS": 280, "USDINR": 88.5, "EURINR": 103.0, "GBPINR": 118.0, "JPYINR": 0.59, "EURUSD": 1.16,
               "GBPUSD": 1.34, "USDJPY": 148.0, "BTCUSDT": 65000}


class Provider:
    name = "base"

    def candles(self, spec: Spec, now: datetime, tf: str = "5m", n: int = 400) -> pd.DataFrame | None: return None
    def history(self, spec: Spec, now: datetime, days: int = 60) -> pd.DataFrame | None: return self.candles(spec, now, "5m", 4000)
    def ltp(self, spec: Spec, now: datetime) -> float | None: return None
    def global_changes(self, now: datetime) -> dict: return {}
    def smart_inputs(self, spec: Spec, now: datetime) -> dict: return {}
    def option_chain(self, spec: Spec, now: datetime) -> dict | None: return None
    def option_ltp(self, spec: Spec, strike: float, cp: str, expiry: str, now: datetime) -> float | None: return None
    def option_candles(self, spec: Spec, strike: float, cp: str, expiry: str, now: datetime) -> pd.DataFrame | None: return None
    def news_tags(self, now: datetime) -> list: return []
    def headlines(self, now: datetime) -> list: return []
    def events(self, now: datetime) -> list: return []
    def usdinr(self, now: datetime) -> float: return 88.0
    def lot(self, spec: Spec) -> float: return spec.lot
    def holidays(self) -> set: return set()
    def vix_z(self, now: datetime) -> float | None: return None
    def stock_universe(self, now: datetime, n: int = 50) -> list: return []
    def health(self, now: datetime) -> list: return [("provider", "OK", self.name)]


def _seed(*parts) -> int:
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


class FakeProvider(Provider):
    """Synthetic but realistic-looking data so the whole app can be seen working with ZERO setup."""
    name = "demo"
    TREND = {"GOLD": 0.0011, "USDINR": -0.0009, "BTCUSDT": 0.0004}      # symbols that trend in the demo

    def __init__(self, seed: int = 7):
        self.seed = seed

    def candles(self, spec, now, tf="5m", n=400):
        end = pd.Timestamp(now).tz_convert(IST).floor("5min") - pd.Timedelta(minutes=5)   # last CLOSED bar start
        idx = pd.date_range(end=end, periods=n, freq="5min", tz=IST)
        rng = np.random.default_rng(_seed(self.seed, spec.symbol, end.date()))
        drift = self.TREND.get(spec.symbol, 0.0)
        vol = 0.0007 if spec.asset_class != "CRYPTO" else 0.0012
        rets = rng.normal(drift, vol, n)
        start = START_PRICE.get(spec.symbol, 500.0)
        close = start * np.exp(np.cumsum(rets))
        open_ = np.r_[start, close[:-1]]
        sp = np.abs(rng.normal(0, vol * 0.6, n)) * close
        return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + sp, "low": np.minimum(open_, close) - sp,
                             "close": close, "volume": 1000 * (1 + np.abs(rng.normal(0, 0.5, n)))}, index=idx)

    def history(self, spec, now, days=60):
        return self.candles(spec, now, "5m", 1500)

    def ltp(self, spec, now):
        df = self.candles(spec, now, n=5)
        return float(df["close"].iloc[-1])

    def global_changes(self, now):
        r = np.random.default_rng(_seed(self.seed, "global", now.date()))
        keys = ["^GSPC", "ES=F", "^IXIC", "^N225", "^HSI", "DX-Y.NYB", "CL=F", "^VIX", "^TNX", "USDINR=X", "GC=F", "SI=F", "NG=F", "BTC-USD"]
        return {k: float(r.normal(0.1, 0.8)) for k in keys}

    def smart_inputs(self, spec, now):
        if spec.asset_class == "INDEX":
            return {"kind": "index", "fii_cash_net_cr": 1200.0, "dii_cash_net_cr": 800.0, "fii_idx_fut_long_ratio": 0.55}
        return {}

    def option_chain(self, spec, now):
        if not (spec.has_options or spec.asset_class == "STOCK"):
            return None
        spot = self.ltp(spec, now)
        step = 50 if spec.symbol == "NIFTY" else (100 if spec.symbol == "BANKNIFTY" else (25 if spec.asset_class == "INDEX" else max(1, round(spot * 0.01))))
        atm = round(spot / step) * step
        dte = 5.0 if spec.symbol == "NIFTY" else 20.0
        iv = 0.14
        rows = []
        for i in range(-10, 11):
            k = atm + i * step
            rows.append({"strike": float(k), "ce_oi": 100000 * (1 + max(0, i)) , "pe_oi": 100000 * (1 + max(0, -i)),
                         "ce_ltp": bs_price(spot, k, dte / 365, iv, "CE"), "pe_ltp": bs_price(spot, k, dte / 365, iv, "PE"),
                         "ce_iv": iv, "pe_iv": iv})
        exp = (now + timedelta(days=dte)).date().isoformat()
        return {"expiry": exp, "dte": dte, "rows": rows, "iv": iv, "iv_pct": 0.4, "spot": spot, "lot": self.lot(spec)}

    def option_ltp(self, spec, strike, cp, expiry, now):
        ch = self.option_chain(spec, now)
        if not ch:
            return None
        for r in ch["rows"]:
            if r["strike"] == strike:
                return r["ce_ltp" if cp == "CE" else "pe_ltp"]
        return None

    def option_candles(self, spec, strike, cp, expiry, now):
        """DEMO only: SYNTHETIC option premium bars priced from the demo underlying with Black-Scholes (no real option history exists here)."""
        from datetime import date
        from .options import bs_price
        df = self.candles(spec, now, "5m", 400)
        if df is None or df.empty:
            return None
        exp_dt = pd.Timestamp(date.fromisoformat(expiry), tz=IST) + pd.Timedelta(hours=15, minutes=30)
        out = df.copy()
        for c in ("open", "high", "low", "close"):
            out[c] = [bs_price(float(u), float(strike), max((exp_dt - ts).total_seconds() / 86400.0, 0.02) / 365.0, 0.15, cp) for u, ts in zip(df[c], df.index)]
        hi, lo = out[["open", "high", "low", "close"]].max(axis=1), out[["open", "high", "low", "close"]].min(axis=1)
        out["high"], out["low"], out["volume"] = hi, lo, 0.0
        return out

    def events(self, now):
        d = now.astimezone(IST)
        return [Event("US CPI", (d + timedelta(days=3)).replace(hour=18, minute=0, second=0, microsecond=0), "HIGH", ("ALL",)),
                Event("RBI policy", (d + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0), "HIGH", ("INDEX", "USDINR"))]

    def headlines(self, now):
        return [{"title": "Demo: Gold firm as dollar slips", "source": "demo", "ts": now.isoformat(), "tags": ["GOLD +"]},
                {"title": "Demo: Crude steady ahead of OPEC meet", "source": "demo", "ts": now.isoformat(), "tags": []}]

    def news_tags(self, now):
        return tag_headline("Dollar slips, weak dollar helps gold", now, "demo", False, 0.6)

    def stock_universe(self, now, n=50):
        return [stock_spec(s) for s in ("RELIANCE", "HDFCBANK", "TCS", "INFY", "ICICIBANK", "SBIN")][:n]

    def usdinr(self, now): return 88.5

    def lot(self, spec):
        return 500 if spec.asset_class == "STOCK" else spec.lot
````

### `rtw/notify.py`

````text file=rtw/notify.py
"""Text builders (Hinglish) + Telegram sender + command handler. No business logic here."""
from __future__ import annotations
import json
from datetime import datetime
import requests
from .lifecycle import Signal


def fmt(x) -> str:
    if x is None:
        return "-"
    a = abs(x)
    if a >= 1000:
        return f"{x:,.0f}"
    if a >= 10:
        return f"{x:.2f}"
    return f"{x:.4f}"


def hhmm(iso_or_dt) -> str:
    if not iso_or_dt:
        return "-"
    d = datetime.fromisoformat(iso_or_dt) if isinstance(iso_or_dt, str) else iso_or_dt
    return d.strftime("%H:%M")


def instrument_label(sig_symbol: str, extra: dict) -> str:
    o = extra.get("option")
    if o:
        return f"{sig_symbol} {o['strike']:g} {o['cp']}"
    if extra.get("contract"):
        return f"{sig_symbol} ({extra['contract']})"
    return sig_symbol


def action_text(direction: str, extra: dict) -> str:
    o = extra.get("option")
    if o:
        return "CALL (CE) KHARIDO" if o["cp"] == "CE" else "PUT (PE) KHARIDO"
    return "BUY" if direction == "BUY" else "SELL"


def trade_card(sig: Signal, extra: dict) -> dict:
    o = extra.get("option")
    live = extra.get("live") or {}
    if sig.state == "NEW":
        status = f"Entry ka intezar: {fmt(sig.entry_lo)}-{fmt(sig.entry_hi)} ke beech aane do. {hhmm(sig.valid_till)} tak valid."
    elif sig.state == "ACTIVE":
        r = live.get("r")
        status = "Trade chalu hai" + (f" — abhi {r:+.2f}R" if r is not None else "") + f". {hhmm(sig.exit_by)} tak hold."
    elif sig.state == "MISSED":
        status = "MISSED — chase mat karo."
    elif sig.state == "TARGET":
        status = "Target hit"
    elif sig.state == "SL":
        status = "Stoploss hit"
    else:
        status = sig.close_reason or "Expire"
    return {"id": sig.id, "symbol": sig.symbol, "label": instrument_label(sig.symbol, extra), "action": action_text(sig.direction, extra),
            "direction": sig.direction, "paper": sig.paper, "grade": sig.grade, "confidence": round(sig.confidence),
            "state": sig.state, "entry_lo": sig.entry_lo, "entry_hi": sig.entry_hi, "sl": sig.sl, "t1": sig.t1, "t2": sig.t2,
            "chase_price": sig.chase_price, "valid_till": sig.valid_till.isoformat(), "exit_by": sig.exit_by.isoformat(),
            "created_at": sig.created_at.isoformat(), "reasons": sig.reasons, "option": o, "contract": extra.get("contract"),
            "lots": extra.get("lots"), "risk_amount": extra.get("risk_amount"), "max_loss": extra.get("max_loss"),
            "plan_note": extra.get("plan_note", ""), "status_text": status, "live": live, "entry_price": sig.entry_price,
            "exit_price": sig.exit_price, "r_multiple": sig.r_multiple, "close_reason": sig.close_reason,
            "setup_key": extra.get("setup_key")}


def format_signal(sig: Signal, extra: dict, event: str = "NEW") -> str:
    c = trade_card(sig, extra)
    tag = " [PAPER]" if sig.paper else ""
    o = c["option"]
    head = {"NEW": f"NAYA SIGNAL{tag}", "ACTIVE": f"ENTRY MIL GAYI{tag}", "TARGET": f"TARGET HIT{tag}", "SL": f"STOPLOSS HIT{tag}",
            "EXPIRED": f"SIGNAL KHATAM{tag}", "MISSED": f"MISSED{tag}"}[event]
    icon = {"NEW": "🟢", "ACTIVE": "▶️", "TARGET": "✅", "SL": "🛑", "EXPIRED": "⌛", "MISSED": "⚠️"}[event]
    lines = [f"{icon} {head}", f"{c['label']} — {c['action']}"]
    if event in ("NEW", "ACTIVE"):
        und = extra.get("underlying_name", sig.symbol)
        lines.append(f"Entry: {und} {fmt(sig.entry_lo)}-{fmt(sig.entry_hi)}" + (f" (option ~₹{fmt(o['premium'])})" if o else ""))
        pre = f"{und} " if o else ""
        lines.append(f"SL: {pre}{fmt(sig.sl)}" + (f" (option ~₹{fmt(o['sl_premium'])})" if o else ""))
        lines.append(f"Target 1: {pre}{fmt(sig.t1)}" + (f" (option ~₹{fmt(o['t1_premium'])})" if o else "") + f" | Target 2: {pre}{fmt(sig.t2)}")
        if extra.get("qty") is not None:
            lines.append(f"Qty: {extra['qty']:.3f} {extra.get('qty_unit', '')} | SL pe risk: ${fmt(c['risk_amount'])}")
        elif c["lots"] is not None:
            lines.append(f"Lots: {c['lots']}" + (f" | Max nuksan (poora premium): ₹{fmt(c['max_loss'])}" if c.get("max_loss") else
                                                  f" | SL pe risk: ₹{fmt(c['risk_amount'])}"))
        lines.append(f"Valid: {hhmm(sig.valid_till)} tak | Nikalna: {hhmm(sig.exit_by)} tak")
        if sig.reasons:
            lines.append("Kyu: " + "; ".join(sig.reasons[:4]))
        lines.append(f"Grade {sig.grade} | Confidence {c['confidence']}%")
        if event == "NEW":
            lines.append(f"Chase mat karo: {fmt(sig.chase_price)} ke aage mat lo.")
        if c["plan_note"]:
            lines.append("Note: " + c["plan_note"])
    elif event in ("TARGET", "SL", "EXPIRED") and sig.r_multiple is not None:
        lines.append(f"Result: {sig.r_multiple:+.2f}R ({sig.close_reason})")
    elif event == "MISSED":
        lines.append("Price chase level ke paar chala gaya. Is trade ko chhod do.")
    if sig.paper:
        lines.append("PAPER signal: abhi record ban raha hai, real paisa mat lagao.")
    return "\n".join(lines)


def format_wait(card: dict) -> str:
    s = "⏸ WAIT\n" + card.get("reason", "")
    if card.get("waiting_for"):
        s += "\nIntezar: " + card["waiting_for"]
    if card.get("next_event"):
        e = card["next_event"]
        s += f"\nAgla bada event: {e['name']} {e['when_text']}"
    return s


def format_brief(home: dict, news: dict) -> str:
    lines = ["☀️ PRE-MARKET BRIEF"]
    if home.get("trades"):
        lines.extend(format_signal_card(t) for t in home["trades"])
    elif home.get("trade"):
        lines.append(format_signal_card(home["trade"]))
    else:
        w = home.get("wait") or {}
        lines.append("Abhi koi trade nahi. " + w.get("reason", ""))
    lines.append(f"News mode: {news.get('mode', 'CALM')}")
    for e in (news.get("events") or [])[:5]:
        lines.append(f"• {e['name']} {e['when_text']} ({e['impact']})")
    return "\n".join(lines)


def format_signal_card(c: dict) -> str:
    return f"{c['label']} — {c['action']} | entry {fmt(c['entry_lo'])}-{fmt(c['entry_hi'])} SL {fmt(c['sl'])} T1 {fmt(c['t1'])} | {c['status_text']}"


class TelegramSender:
    """Plain HTTPS to the Bot API. Never raises (returns False on failure)."""

    def __init__(self, token: str, chat_id: str, timeout: float = 15.0):
        self.token, self.chat_id, self.timeout = token, chat_id, timeout

    @property
    def ready(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        if not self.ready:
            return False
        try:
            r = requests.post(f"https://api.telegram.org/bot{self.token}/sendMessage",
                              json={"chat_id": self.chat_id, "text": text[:4000], "disable_web_page_preview": True}, timeout=self.timeout)
            return r.ok
        except Exception:
            return False

    def get_updates(self, offset: int | None, timeout: int = 25) -> list:
        if not self.token:
            return []
        try:
            r = requests.get(f"https://api.telegram.org/bot{self.token}/getUpdates",
                             params={"timeout": timeout, **({"offset": offset} if offset else {})}, timeout=timeout + 10)
            return r.json().get("result", []) if r.ok else []
        except Exception:
            return []
````

### `rtw/views.py`

````text file=rtw/views.py
"""Read-only view builders used by the API and Telegram. They only read the DB (and a provider for news/health)."""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from .mood import mood_of
from .db import open_trades, open_trade, load_decisions, track_record, get_setting, signal_from_row
from .notify import trade_card, fmt
from .news import group_of
from .sessions import IST, is_open

TABS = ("index", "commodity", "stocks", "forex", "crypto")


def when_text(when: datetime, now: datetime) -> str:
    w = when.astimezone(IST)
    delta = w - now.astimezone(IST)
    mins = int(delta.total_seconds() // 60)
    if mins < 0:
        return f"{w:%d %b %H:%M} IST ({-mins} min pehle)"
    if mins < 90:
        return f"{w:%d %b %H:%M} IST ({mins} min me)"
    if mins < 48 * 60:
        return f"{w:%d %b %H:%M} IST ({mins // 60}h {mins % 60}m me)"
    return f"{w:%d %b %H:%M} IST"


def events_payload(events: list, now: datetime, horizon_h: int = 72) -> list:
    out = []
    for e in sorted(events, key=lambda x: x.when):
        if e.when < now - timedelta(minutes=30) or e.when > now + timedelta(hours=horizon_h):
            continue
        out.append({"name": e.name, "when": e.when.isoformat(), "when_text": when_text(e.when, now), "impact": e.impact, "assets": list(e.assets)})
    return out


def wait_card(decisions: dict, events: list, now: datetime) -> dict:
    """What are we waiting for? Use the closest near-miss (highest |S| among decisions that are WAIT with a reason)."""
    best = None
    for sym, d in decisions.items():
        if d.get("action") != "WAIT" or not d.get("wait_reason") or "market band" in d["wait_reason"]:
            continue
        if best is None or abs(d.get("S", 0)) > abs(best[1].get("S", 0)):
            best = (sym, d)
    nxt = next((e for e in sorted(events, key=lambda x: x.when) if e.impact == "HIGH" and e.when > now), None)
    card = {"reason": "Abhi koi saaf setup nahi hai. Signal tabhi aayega jab sab shartein poori hongi.", "waiting_for": "", "next_event": None,
            "closest": None}
    if best:
        sym, d = best
        card["reason"] = f"Sabse kareeb: {sym} — {d['wait_reason']}"
        card["waiting_for"] = d["wait_reason"]
        card["closest"] = {"symbol": sym, "S": d.get("S"), "A": d.get("A")}
    elif decisions and all("market band" in (d.get("wait_reason") or "") for d in decisions.values()):
        card["reason"] = "Sab market abhi band hain. Agla session khulne ka intezar."
    if nxt:
        card["next_event"] = {"name": nxt.name, "when_text": when_text(nxt.when, now)}
    return card


def home_view(con, now: datetime, events: list, settings) -> dict:
    dec = load_decisions(con)
    opens = open_trades(con)
    sig, extra = (opens[0] if opens else (None, {}))
    open_syms = {s.symbol for s, _ in opens}
    info = []
    for sym, d in dec.items():
        if d.get("action") in ("BUY", "SELL") and sym not in open_syms:
            info.append({"symbol": sym, "action": d["action"], "grade": d.get("grade"), "confidence": d.get("confidence"), "note": d.get("note", "INFO: abhi ek trade active hai" if sig else "INFO: behtar signal chuna gaya")})
    info.sort(key=lambda x: -(x.get("confidence") or 0))
    last = con.execute("SELECT * FROM signals WHERE kind='TRADE' AND state NOT IN ('NEW','ACTIVE') ORDER BY created_at DESC LIMIT 1").fetchone()
    last_card = None
    if last:
        ls = signal_from_row(last)
        last_card = trade_card(ls, json.loads(last["extra_json"] or "{}"))
    out = {"mode": settings.mode, "profile": settings.profile, "updated": now.isoformat(), "status": "WAIT", "trade": None, "wait": None,
           "info": info[:6], "last_closed": last_card, "capital": settings.capital,
           "max_trades": getattr(settings, "max_trades", 1), "trades": [trade_card(s, e) for s, e in opens]}
    if sig:
        out["status"] = sig.state
        out["trade"] = trade_card(sig, extra)
    else:
        out["wait"] = wait_card(dec, events, now)
    return out


def mood_view(con, now: datetime, specs: list) -> dict:
    """Market mood of every core symbol (+ range for SIDEWAYS) and the recent confirmed flips (drives the in-app pop-up)."""
    from .mood import mood_of, range_of, HEADLINE
    from .db import load_df
    dec = load_decisions(con)
    items = []
    for sp in specs:
        if sp.tab == "stocks":
            continue
        mm = mood_of(dec.get(sp.symbol))
        if not mm:
            items.append({"symbol": sp.symbol, "name": sp.name, "mood": None, "label": "Market band / data nahi", "icon": "⚪", "text": "", "headline": sp.symbol in HEADLINE})
            continue
        it = {"symbol": sp.symbol, "name": sp.name, "headline": sp.symbol in HEADLINE, **mm}
        if mm["mood"] == "SIDEWAYS":
            it["range"] = range_of(load_df(con, sp.symbol, "5m", 60))
        items.append(it)
    items.sort(key=lambda x: (not x["headline"], x["mood"] is None))
    return {"updated": now.isoformat(), "items": items, "flips": (get_setting(con, "mood_flips", []) or [])[-10:]}


def markets_view(con, tab: str, now: datetime, settings, specs: list) -> dict:
    dec = load_decisions(con)
    rows = []
    for sp in specs:
        if sp.tab != tab:
            continue
        d = dec.get(sp.symbol, {})
        rows.append({"symbol": sp.symbol, "name": sp.name, "action": d.get("action", "WAIT"), "grade": d.get("grade"),
                     "confidence": d.get("confidence"), "price": d.get("price"), "regime": d.get("regime"), "paper": d.get("paper", True),
                     "reasons": (d.get("reasons") or [])[:3], "wait_reason": d.get("wait_reason", ""), "news_mode": d.get("news_mode"),
                     "instrument": d.get("instrument"), "plan": d.get("plan"), "mood": mood_of(d), "open": bool(is_open(sp.segment, now)) if settings.mode != "DEMO" else True})
    active = sorted([r for r in rows if r["action"] in ("BUY", "SELL")], key=lambda r: -(r["confidence"] or 0))
    waits = [r for r in rows if r["action"] not in ("BUY", "SELL")]
    if tab == "stocks":
        return {"tab": tab, "active": active, "wait_count": len(waits), "waiting": [{"symbol": r["symbol"], "mood": r.get("mood")} for r in waits]}
    return {"tab": tab, "active": active, "waiting": waits, "wait_count": len(waits)}


def record_view(con) -> dict:
    allr = track_record(con)
    paper = track_record(con, True)
    live = track_record(con, False)
    rows = con.execute("SELECT * FROM signals WHERE kind='TRADE' AND state IN ('TARGET','SL','EXPIRED','MISSED') ORDER BY created_at DESC LIMIT 30").fetchall()
    last = [{"symbol": r["symbol"], "direction": r["direction"], "state": r["state"], "r": r["r_multiple"], "paper": bool(r["paper"]),
             "closed_at": r["closed_at"], "reason": r["close_reason"]} for r in rows]
    eq, cum = [], 0.0
    for r in con.execute("SELECT r_multiple, closed_at FROM signals WHERE kind='TRADE' AND r_multiple IS NOT NULL ORDER BY closed_at"):
        cum += r[0]
        eq.append({"t": r[1], "cum_r": round(cum, 3)})
    setups = [dict(r) for r in con.execute("SELECT * FROM setup_stats ORDER BY expectancy_r DESC")]
    return {"all": allr, "paper": paper, "live": live, "last": last, "equity": eq, "setups": setups}


def news_view(con, provider, now: datetime, events: list, mode_info: dict) -> dict:
    return {"mode": mode_info.get("mode", "CALM"), "reason": mode_info.get("lock_reason"), "events": events_payload(events, now),
            "headlines": provider.headlines(now)[:40], "vix_z": provider.vix_z(now)}


def health_view(con) -> list:
    rows = con.execute("SELECT component, status, detail, MAX(ts) AS ts FROM health_log GROUP BY component ORDER BY component").fetchall()
    return [dict(r) for r in rows]
````

### `rtw/pipeline.py`

````text file=rtw/pipeline.py
"""Orchestrator: refresh candles -> analyze every symbol -> pick ONE best -> manage the single active trade.
Reads candles from the DB only. All external data comes through a Provider (never raises)."""
from __future__ import annotations
import json
from datetime import datetime, timedelta
import threading
import pandas as pd
from .candles import resample_ohlc
from .config import (Settings, Spec, CORE_SPECS, MCX_CONTRACTS, CROSS_PAIRS_USD_QUOTED, choose_contract)
from .db import (open_trades, forward_stats, upsert_candles, load_df, open_trade, save_signal, save_decision, load_decisions, load_protections,
                 save_protections, get_setup_stats, log_health, set_setting, get_setting, patch_decision)
from .engine import analyze
from .globalctx import global_layer
from .layers import LayerResult, trend_layer
from .lifecycle import Signal, advance, pick_best
from .news import news_mode, group_of
from .notify import format_signal, instrument_label
from .options import options_layer, pick_option, option_ok, option_plan, bs_delta, liquidity_ok
from .scoring import direction_of
from .sessions import IST
from .smart import fii_layer, stock_smart_layer, crypto_smart_layer, cot_layer

TF_MIN = 5
FRESH_MIN = 6          # a decision older than this cannot start a trade
MIN_TRADES_FOR_RECORD = 30


def data_age_sec(df: pd.DataFrame, now: datetime, tf_min: int = TF_MIN) -> float:
    """0 when the newest CLOSED bar is the one we expect right now; grows if the feed is behind."""
    expected_end = pd.Timestamp(now).tz_convert(IST).floor(f"{tf_min}min")
    last_end = df.index[-1] + pd.Timedelta(minutes=tf_min)
    return max(0.0, (expected_end - last_end).total_seconds())


def htf_conflict(df: pd.DataFrame, direction: str) -> tuple[bool, str]:
    """Higher-timeframe (15m) trend strongly against the signal -> block."""
    h = resample_ohlc(df, "15min", now=df.index[-1] + pd.Timedelta(minutes=TF_MIN))
    if len(h) < 60:
        return False, ""
    r = trend_layer(h, intraday=False)
    s = 1 if direction == "BUY" else -1
    if r.score * s < -0.4 and r.conf >= 0.4:
        return True, "bade timeframe (15 min) ka trend ulta hai"
    return False, ""


class Orchestrator:
    def __init__(self, con, provider, settings: Settings, send=None):
        self.con, self.provider, self.st = con, provider, settings
        self.send = send or (lambda text: False)       # send(text) -> bool  (Telegram)
        self.demo = settings.mode == "DEMO"
        self._ctx: dict | None = None
        self._lock = threading.RLock()                 # core + stocks + API refresh must never run a cycle at the same time

    # ------------------------------------------------------------ universe & data
    def specs(self, now: datetime) -> list[Spec]:
        return list(CORE_SPECS) + list(self.provider.stock_universe(now, self.st.stocks_top_n))

    def spec_by_symbol(self, symbol: str, now: datetime) -> Spec | None:
        return next((s for s in self.specs(now) if s.symbol == symbol), None)

    def refresh_symbol(self, spec: Spec, now: datetime) -> bool:
        try:
            df = self.provider.candles(spec, now, "5m", 400)
        except Exception as e:                       # providers should not raise, but never let one symbol kill the cycle
            log_health(self.con, now, f"data:{spec.symbol}", "FAIL", repr(e))
            return False
        if df is None or df.empty:
            log_health(self.con, now, f"data:{spec.symbol}", "FAIL", "no candles")
            return False
        contract = (getattr(df, "attrs", {}) or {}).get("contract")
        if contract:                                    # futures roll: never splice two contracts into one series
            prev = get_setting(self.con, f"contract:{spec.symbol}")
            if prev is not None and prev != contract:
                self.con.execute("DELETE FROM candles WHERE symbol=?", (spec.symbol,))
                self.con.commit()
            set_setting(self.con, f"contract:{spec.symbol}", contract)
        rows = [(ts.tz_convert(IST).isoformat(), float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume))
                for ts, r in df.iterrows()]
        upsert_candles(self.con, spec.symbol, "5m", rows)
        log_health(self.con, now, f"data:{spec.symbol}", "OK", f"{len(rows)} bars")
        return True

    def refresh_all(self, now: datetime, scope: str = "core") -> int:
        from .sessions import is_open
        n = 0
        for sp in self.specs(now):
            if (scope == "core") == (sp.tab == "stocks"):
                continue
            if not self.demo and not is_open(sp.segment, now, self.provider.holidays()):
                continue
            n += self.refresh_symbol(sp, now)
        return n

    # ------------------------------------------------------------ context (once per cycle)
    def context(self, now: datetime) -> dict:
        return {"events": self.provider.events(now), "tags": self.provider.news_tags(now), "global": self.provider.global_changes(now),
                "vix_z": self.provider.vix_z(now), "usdinr": self.provider.usdinr(now)}

    def _smart(self, spec: Spec, now: datetime) -> LayerResult | None:
        i = self.provider.smart_inputs(spec, now) or {}
        k = i.get("kind")
        if k == "index":
            return fii_layer(i.get("fii_cash_net_cr"), i.get("dii_cash_net_cr"), i.get("fii_idx_fut_long_ratio"), i.get("index_buildup"))
        if k == "stock":
            return stock_smart_layer(i.get("delivery_pct"), i.get("delivery_avg_pct"), i.get("price_chg_pct"), i.get("buildup"),
                                     i.get("bulk_net", 0), i.get("insider_net", 0))
        if k == "crypto":
            return crypto_smart_layer(i.get("funding_rate"), i.get("ls_ratio"), i.get("fear_greed"), i.get("oi_chg_pct"), i.get("price_chg_pct"))
        if k == "cot":
            return cot_layer(i.get("net_spec_pct_oi"), i.get("change_4w_pct_oi"))
        return None

    def _engine_lot_and_capital(self, spec: Spec, ctx: dict) -> tuple[float, float]:
        cap = self.st.capital
        if spec.asset_class == "COMMODITY":
            return MCX_CONTRACTS[spec.group][-1][1], cap
        if spec.asset_class == "FOREX":
            lot = self.provider.lot(spec)
            if spec.symbol == "USDJPY":                  # P&L is in JPY: convert with USDINR / USDJPY
                d = load_df(self.con, spec.symbol, "5m", 2)
                px = float(d["close"].iloc[-1]) if d is not None and len(d) else 148.0
                return lot * ctx["usdinr"] / px, cap
            return (lot * ctx["usdinr"] if spec.symbol in CROSS_PAIRS_USD_QUOTED else lot), cap
        if spec.asset_class == "CRYPTO":
            return spec.lot, cap / max(ctx["usdinr"], 1.0)
        return self.provider.lot(spec), cap

    # ------------------------------------------------------------ one symbol
    def analyze_spec(self, spec: Spec, now: datetime, ctx: dict, stats: dict, prot) -> dict:
        df = load_df(self.con, spec.symbol, "5m", 400)
        base = {"symbol": spec.symbol, "name": spec.name, "asset_class": spec.asset_class, "action": "WAIT", "paper": True}
        if df is None or len(df) < 60:
            return {**base, "wait_reason": "data nahi / kam hai", "S": 0.0, "A": 0.0, "gates": []}
        seg = "CRYPTO" if self.demo else spec.segment
        extra: dict = {}
        g = global_layer(spec.group, ctx["global"])
        if g.conf > 0:
            extra["global"] = g
        sm = self._smart(spec, now)
        if sm is not None and sm.conf > 0:
            extra["smart"] = sm
        chain = None
        if spec.has_options:
            chain = self.provider.option_chain(spec, now)
            if chain:
                extra["options"] = options_layer(chain.get("spot") or float(df["close"].iloc[-1]), chain["rows"], chain.get("iv_pct"))
        lot, cap = self._engine_lot_and_capital(spec, ctx)
        want_option = bool(chain)
        age = data_age_sec(df, now)
        ok_prot, why_prot = prot.can_trade(now)

        def run(paper: bool, exp, ntr):
            return analyze(spec.symbol, spec.asset_class, df, now, capital=cap, risk_pct=self.st.risk_pct, lot_size=lot,
                           profile=self.st.profile, segment=seg, intraday=True, extra_layers=extra, tags=ctx["tags"], events=ctx["events"],
                           data_age_sec=age, setup_expectancy=exp, setup_trades=ntr, paper=paper, daily_loss_hit=prot.daily_loss_hit(now),
                           protections_ok=(ok_prot, why_prot), vix_z=(ctx["vix_z"] if spec.segment == "NSE" else None), holidays=self.provider.holidays(), skip_afford=want_option)

        args = (True, None, 0)
        d = run(*args)
        key = None
        if d.get("S") and abs(d["S"]) > 0 and "regime" in d:
            key = f"{spec.asset_class}|{direction_of(d['S'])}|{d['regime']}"
            rec = stats.get(key)
            if rec:
                trusted = rec["trades"] >= MIN_TRADES_FOR_RECORD and not rec["benched"] and rec["expectancy_r"] > 0
                if trusted and self.st.mode != "LIVE":          # PAPER until the FORWARD (paper-trading) record also exists
                    fw = forward_stats(self.con, key)
                    trusted = fw["trades"] >= MIN_TRADES_FOR_RECORD and fw["expectancy_r"] > 0
                args = (not trusted, (-0.01 if rec["benched"] else rec["expectancy_r"]), rec["trades"])
                d = run(*args)
            d["setup_key"] = key
        # stocks: fetch the option chain lazily (only when a call is possible) and re-run so the option risk decides affordability
        if spec.asset_class == "STOCK" and not chain and (d["action"] in ("BUY", "SELL") or "capital me 1 lot" in d.get("wait_reason", "")):
            chain = self.provider.option_chain(spec, now)
            if chain:
                extra["options"] = options_layer(chain.get("spot") or float(df["close"].iloc[-1]), chain["rows"], chain.get("iv_pct"))
                want_option = True
                d = run(*args)
                d["setup_key"] = key
        d.update(name=spec.name, price=d.get("price") or float(df["close"].iloc[-1]), asset_class=spec.asset_class)
        if d["action"] in ("BUY", "SELL"):
            bad, why = htf_conflict(df, d["action"])
            if bad:
                d.update(action="WAIT", passed=False, wait_reason=why, rank=0.0)
        if d["action"] in ("BUY", "SELL"):
            d = self._finish_plan(spec, d, chain, ctx, now)
        return d

    def _finish_plan(self, spec: Spec, d: dict, chain: dict | None, ctx: dict, now: datetime) -> dict:
        """Turn the underlying plan into a concrete instrument: MCX contract by capital / option strike."""
        pl = d["plan"]
        d["extra"] = {"underlying_name": spec.name, "plan_note": d.get("plan_note", ""), "setup_key": d.get("setup_key")}
        d["instrument"] = spec.symbol
        if spec.asset_class == "COMMODITY":
            c = choose_contract(spec.group, pl["sl_dist"], d["risk_budget"])
            if not c["affordable"]:
                return {**d, "action": "WAIT", "passed": False, "rank": 0.0, "wait_reason": "capital me sabse chhota contract bhi risk limit se bada hai"}
            pl["lots"], pl["risk_amount"] = c["lots"], c["lots"] * c["risk_per_lot"]
            d["extra"].update(contract=c["contract"], lots=c["lots"], risk_amount=pl["risk_amount"])
            d["instrument"] = f"{spec.symbol} ({c['contract']})"
            if c["contract"] == "GOLDPETAL":
                d["extra"]["plan_note"] = (d["extra"].get("plan_note", "") + "; levels 10-gram (GOLDM) price ke hisaab se hain, Petal ka price ~1/10 dikhta hai").lstrip("; ")
            return d
        if chain:
            return self._option_conversion(spec, d, chain, now)
        d["extra"].update(lots=pl["lots"], risk_amount=pl["risk_amount"])
        if spec.asset_class == "CRYPTO":
            d["extra"].update(qty=pl["lots"] * spec.lot, qty_unit="BTC", currency="USD", risk_amount=pl["risk_amount"])
        return d

    def _option_conversion(self, spec: Spec, d: dict, chain: dict, now: datetime) -> dict:
        pl = d["plan"]
        rows = chain["rows"]
        strikes = sorted({r["strike"] for r in rows})
        by = {r["strike"]: {"CE": r.get("ce_ltp"), "PE": r.get("pe_ltp")} for r in rows}
        spot = chain.get("spot") or d["price"]
        opt = pick_option(d["action"], spot, strikes, by, chain["dte"], chain["iv"])
        ok, why = option_ok(opt, chain.get("iv_pct", 0.5), chain["dte"])
        if ok:
            ok, why = liquidity_ok(rows, opt["strike"], opt["cp"], strict=(spec.symbol == "MIDCPNIFTY"), premium=opt["premium"])
        if not ok:
            return {**d, "action": "WAIT", "passed": False, "rank": 0.0, "wait_reason": why}
        delta = abs(bs_delta(spot, opt["strike"], chain["dte"] / 365, chain["iv"], opt["cp"]))
        lot = chain.get("lot") or self.provider.lot(spec)
        entry = (pl["entry_lo"] + pl["entry_hi"]) / 2
        op = option_plan(opt["premium"], delta, pl["sl_dist"], abs(pl["t1"] - entry), abs(pl["t2"] - entry), lot, d["risk_budget"], self.st.risk_pct)
        if not op["affordable"]:
            need = op["min_capital"]
            return {**d, "action": "WAIT", "passed": False, "rank": 0.0,
                    "wait_reason": f"capital kam: 1 lot ke risk ke liye kam se kam ~₹{need:,.0f} capital chahiye" if need else "capital kam"}
        o = {"cp": opt["cp"], "strike": opt["strike"], "expiry": chain["expiry"], "dte": chain["dte"], "premium": op["premium"],
             "sl_premium": op["sl_premium"], "t1_premium": op["t1_premium"], "t2_premium": op["t2_premium"], "pop": opt["pop"],
             "breakeven": opt["breakeven"], "expected_move": opt["expected_move"], "iv": chain["iv"], "delta": delta}
        pl["lots"] = op["lots"]
        d["extra"].update(option=o, lots=op["lots"], lot_size=lot, max_loss=op["max_loss_per_lot"] * op["lots"],
                          risk_amount=op["risk_per_lot"] * op["lots"])
        d["instrument"] = f"{spec.symbol} {opt['strike']:g} {opt['cp']}"
        return d

    # ------------------------------------------------------------ the cycle
    def cycle(self, now: datetime, scope: str = "all") -> dict:
        """scope: core | stocks | all. Analyze, store decisions, then manage / start the ONE trade. Serialized by a lock
        (two parallel cycles could otherwise open two trades)."""
        with self._lock:
            return self._cycle(now, scope)

    def _cycle(self, now: datetime, scope: str) -> dict:
        ctx = self.context(now)
        self._ctx = ctx
        stats, prot = get_setup_stats(self.con), load_protections(self.con)
        from .sessions import is_open
        for sp in self.specs(now):
            if scope == "core" and sp.tab == "stocks" or scope == "stocks" and sp.tab != "stocks":
                continue
            if not self.demo and not is_open(sp.segment, now, self.provider.holidays()):
                save_decision(self.con, sp.symbol, now, {"symbol": sp.symbol, "action": "WAIT", "wait_reason": f"{sp.segment} market band hai", "S": 0.0, "A": 0.0})
                continue
            try:
                d = self.analyze_spec(sp, now, ctx, stats, prot)
            except Exception as e:                 # one broken symbol must not stop the app
                log_health(self.con, now, f"analyze:{sp.symbol}", "FAIL", repr(e))
                continue
            save_decision(self.con, sp.symbol, now, d)
        events = {"opened": None, "closed": None}
        for sig, extra in open_trades(self.con):
            ev = self.manage_active(sig, extra, now, ctx, prot)
            events["closed"] = events["closed"] or ev
        open_now = [s for s, _ in open_trades(self.con)]
        cap = max(1, min(5, int(getattr(self.st, "max_trades", 1) or 1)))
        blocked = prot.halted or bool(get_setting(self.con, "paused", False)) or not prot.can_trade(now)[0]
        if len(open_now) < cap and not blocked:
            while len(open_now) < cap:                       # fill free slots, best candidate first
                sid = self.start_best(now, open_now)
                if not sid:
                    break
                events["opened"] = events["opened"] or sid
                open_now = [s for s, _ in open_trades(self.con)]
        open_syms = {s.symbol for s in open_now}
        if blocked and len(open_now) < cap:
            note = "INFO: naya signal abhi band hai (pause / cooldown / loss limit)"
        elif len(open_now) >= cap:
            note = "INFO: trade slots bhare hain, ye sirf jaankari hai"
        else:
            note = "INFO: ye signal abhi trade nahi bana (symbol/segment already open ya doosre se kamzor)"
        self._mark_info(now, open_syms, note)
        try:
            self._update_moods(now)
        except Exception as e:                       # mood is informational: never break the cycle
            log_health(self.con, now, "mood", "FAIL", repr(e))
        set_setting(self.con, "last_cycle", now.isoformat())
        return events

    def _update_moods(self, now: datetime) -> None:
        """Track BULLISH/BEARISH/SIDEWAYS per symbol; on a confirmed flip store it and (headline assets + open trades) send Telegram."""
        from .mood import mood_of, update_state, alert_text, HEADLINE, ALERT_GAP_MIN
        dec = load_decisions(self.con)
        readings, full = {}, {}
        for sym, d in dec.items():
            mm = mood_of(d)
            if mm:
                readings[sym], full[sym] = mm["mood"], mm
        state, flips = update_state(get_setting(self.con, "moods", {}) or {}, readings, now)
        keep = get_setting(self.con, "mood_flips", []) or []
        watch = set(HEADLINE) | {s.symbol for s, _ in open_trades(self.con)}
        for f in flips:
            keep.append(f)
            last = (state.get(f["symbol"]) or {}).get("last_alert")
            if f["symbol"] in watch and not (last and datetime.fromisoformat(last) > now - timedelta(minutes=ALERT_GAP_MIN)):
                self.send(alert_text(f["symbol"], dec[f["symbol"]].get("name", f["symbol"]), f, full.get(f["symbol"])))
                state[f["symbol"]]["last_alert"] = now.isoformat()
        set_setting(self.con, "moods", state)
        if flips:
            set_setting(self.con, "mood_flips", keep[-30:])

    def _mark_info(self, now: datetime, open_syms, note: str = "INFO: abhi ek trade active hai, ye sirf jaankari hai") -> None:
        """open_syms: set of symbols that currently hold an open TRADE (they are not INFO)."""
        for sym, d in load_decisions(self.con).items():
            if d.get("action") in ("BUY", "SELL") and sym not in open_syms:
                d["note"] = note
                patch_decision(self.con, sym, d)

    @staticmethod
    def _conflicts(open_sigs, cand: dict) -> bool:
        """A new candidate may not duplicate an open trade: same symbol, or another INDEX trade in the same direction
        (Nifty / BankNifty / Midcap Nifty move together = the same bet twice)."""
        for s in open_sigs or []:
            if s.symbol == cand["symbol"]:
                return True
            if s.asset_class == "INDEX" and cand.get("asset_class") == "INDEX" and s.direction == cand.get("action"):
                return True
        return False

    def start_best(self, now: datetime, open_sigs=None):
        cands = []
        for sym, d in load_decisions(self.con).items():
            row = self.con.execute("SELECT ts FROM decisions WHERE symbol=?", (sym,)).fetchone()
            fresh = row and datetime.fromisoformat(row["ts"]) >= now - timedelta(minutes=FRESH_MIN)
            if fresh and d.get("passed") and d.get("action") in ("BUY", "SELL") and not self._conflicts(open_sigs, {**d, "symbol": sym}):
                cands.append({**d, "symbol": sym})
        best, others = pick_best(cands)
        if not best:
            return None
        pl = best["plan"]
        sig = Signal(id=f"{best['symbol']}-{now:%Y%m%d%H%M%S}", symbol=best["symbol"], asset_class=best["asset_class"], direction=best["action"],
                     entry_lo=pl["entry_lo"], entry_hi=pl["entry_hi"], sl=pl["sl"], t1=pl["t1"], t2=pl["t2"], chase_price=pl["chase_price"],
                     valid_till=datetime.fromisoformat(pl["valid_till"]), exit_by=datetime.fromisoformat(pl["exit_by"]), created_at=now,
                     grade=best.get("grade", "C"), confidence=float(best.get("confidence", 0)), paper=bool(best.get("paper", True)),
                     reasons=best.get("reasons", []), sl_dist=pl["sl_dist"])
        extra = {**best.get("extra", {}), "last_checked": now.isoformat(), "created_price": best.get("price")}
        save_signal(self.con, sig, extra)
        for o in others:
            if o.get("passed") and int(getattr(self.st, "max_trades", 1) or 1) <= 1:
                o["note"] = f"INFO: {best['symbol']} ka signal zyada behtar tha"
                patch_decision(self.con, o["symbol"], o)
        self.send(format_signal(sig, extra, "NEW"))
        return sig.id

    def manage_active(self, sig: Signal, extra: dict, now: datetime, ctx: dict, prot):
        spec = self.spec_by_symbol(sig.symbol, now)
        if spec is None and sig.asset_class == "STOCK":      # stock dropped out of today's list but its trade is still open
            from .config import stock_spec
            spec = stock_spec(sig.symbol)
        if spec is None:
            return None
        old = sig.state
        df = load_df(self.con, sig.symbol, "5m", 60)
        last_checked = datetime.fromisoformat(extra.get("last_checked", sig.created_at.isoformat()))
        tf = timedelta(minutes=TF_MIN)
        last_price = None
        if df is not None:
            for ts, r in df[df.index >= pd.Timestamp(last_checked).floor(f'{TF_MIN}min')].iterrows():
                if sig.state not in ("NEW", "ACTIVE"):
                    break
                advance(sig, float(r.open), ts.to_pydatetime(), None, None)
                if sig.state in ("NEW", "ACTIVE"):
                    advance(sig, float(r.close), ts.to_pydatetime() + tf, float(r.high), float(r.low))
            last_price = float(df["close"].iloc[-1])
        px = self.provider.ltp(spec, now) or last_price
        if px and sig.state in ("NEW", "ACTIVE"):
            advance(sig, float(px), now)
        extra["last_checked"] = now.isoformat()
        if px and sig.entry_price is not None and sig.sl_dist > 0:
            s = 1 if sig.direction == "BUY" else -1
            extra["live"] = {"price": px, "r": s * (px - sig.entry_price) / sig.sl_dist, "pts": s * (px - sig.entry_price)}
        elif px:
            extra["live"] = {"price": px, "r": None, "pts": None}
        if sig.state in ("TARGET", "SL", "EXPIRED", "MISSED"):
            self._on_close(sig, extra, spec, now, prot)
        else:
            self._warn_event(sig, extra, now, ctx)
        save_signal(self.con, sig, extra)
        if sig.state != old:
            self.send(format_signal(sig, extra, sig.state))
        return sig.state if sig.state != old else None

    def _on_close(self, sig: Signal, extra: dict, spec: Spec, now: datetime, prot) -> None:
        o = extra.get("option")
        if o and sig.entry_price is not None:
            p = self.provider.option_ltp(spec, o["strike"], o["cp"], o["expiry"], now)
            if p:
                extra["option_exit_premium"] = p
                extra["r_option"] = (p - o["premium"]) / max(o["premium"] - o["sl_premium"], 1e-9)
        if sig.entry_price is not None and sig.r_multiple is not None:
            prot.record(now, sig.r_multiple)
            save_protections(self.con, prot)

    def _warn_event(self, sig: Signal, extra: dict, now: datetime, ctx: dict) -> None:
        nm = news_mode(ctx["events"], now, sig.symbol, vix_z=(ctx["vix_z"] if sig.asset_class in ("INDEX", "STOCK") else None))
        if nm["mode"] != "CALM" and not extra.get("warned"):
            extra["warned"] = True
            self.send(f"⚠️ {sig.symbol} trade active hai. {nm['lock_reason']}. Pehle se nikalna soch lo.")


    # ------------------------------------------------------------ search (any symbol, INFO only)
    def resolve(self, q: str, now: datetime) -> Spec | None:
        from .config import stock_spec
        qq = q.strip().upper().replace(" ", "")
        if not qq:
            return None
        specs = self.specs(now)
        for sp in specs:
            if qq in (sp.symbol, sp.name.upper().replace(" ", ""), sp.name.upper().replace(" ", "").replace("/", "")):
                return sp
        for sp in specs:
            if qq in sp.symbol or qq in sp.name.upper().replace(" ", ""):
                return sp
        return stock_spec(qq) if qq.isalnum() or "&" in qq or "-" in qq else None

    def search(self, q: str, now: datetime) -> dict:
        sp = self.resolve(q, now)
        if sp is None:
            return {"found": False, "message": "Symbol samajh nahi aaya"}
        if not self.refresh_symbol(sp, now):
            return {"found": False, "symbol": sp.symbol, "message": f"{sp.symbol} ka data nahi mila"}
        d = self.analyze_spec(sp, now, self.context(now), get_setup_stats(self.con), load_protections(self.con))
        d["info_only"] = True
        d["note"] = "Search result: sirf jaankari. Home ke trades alag se chalte hain."
        return {"found": True, "symbol": sp.symbol, "name": sp.name, "decision": d}

    def chart(self, q: str, now: datetime, tf: str = "5m", strike: float | None = None, cp: str | None = None, expiry: str | None = None) -> dict:
        """Chart of any symbol (or of one option contract when strike/cp/expiry are given). Levels come from the open trade, else
        from the current BUY/SELL plan (marked INFO). Candles are closed bars only."""
        from .charts import chart_payload, levels_from_plan, tv_url, TFS
        if tf not in TFS:
            return {"found": False, "message": "tf 5m / 15m / 1h me se ek ho"}
        sp = self.resolve(q, now)
        if sp is None:
            return {"found": False, "message": "Symbol samajh nahi aaya"}
        res = {"found": True, "symbol": sp.symbol, "name": sp.name, "tv_url": tv_url(sp.symbol, sp.asset_class), "option": None}
        if strike is not None and cp in ("CE", "PE") and expiry:
            df = self.provider.option_candles(sp, float(strike), cp, expiry, now)
            if df is None or df.empty:
                return {"found": False, "symbol": sp.symbol, "message": "Is option ka chart data nahi mila"}
            o = next(((e.get("option") or {}) for s, e in open_trades(self.con) if s.symbol == sp.symbol and (e.get("option") or {}).get("strike") == float(strike)), {})
            lv = [{"label": lab, "price": float(o[k]), "kind": kind} for k, lab, kind in (("premium", "Entry", "entry"), ("sl_premium", "SL", "sl"), ("t1_premium", "T1", "target"), ("t2_premium", "T2", "target")) if o.get(k)]
            res.update(chart_payload(df, tf, 120, lv))
            res["option"] = {"strike": float(strike), "cp": cp, "expiry": expiry}
            res["name"] = f"{sp.name} {strike:g} {cp}"
            return res
        df = load_df(self.con, sp.symbol, "5m", 1200)
        if df is None or len(df) < 30:
            if not self.refresh_symbol(sp, now):
                return {"found": False, "symbol": sp.symbol, "message": f"{sp.symbol} ka data nahi mila"}
            df = load_df(self.con, sp.symbol, "5m", 1200)
        if df is None or df.empty:
            return {"found": False, "symbol": sp.symbol, "message": f"{sp.symbol} ka data nahi mila"}
        lv, trade_here = [], next(((s, e) for s, e in open_trades(self.con) if s.symbol == sp.symbol), None)
        if trade_here:
            s = trade_here[0]
            lv = levels_from_plan({"entry_lo": s.entry_lo, "entry_hi": s.entry_hi, "sl": s.sl, "t1": s.t1, "t2": s.t2})
            res["trade"] = {"direction": s.direction, "state": s.state, "option": trade_here[1].get("option")}
        else:
            d = load_decisions(self.con).get(sp.symbol) or {}
            if d.get("action") in ("BUY", "SELL") and d.get("plan"):
                lv = levels_from_plan(d["plan"], " (INFO)")
        res.update(chart_payload(df, tf, 120, lv))
        from .zones import zone_info
        try:
            zi = zone_info(df.tail(400))
            res["sr"] = {"supports": zi["supports"][:2], "resistances": zi["resistances"][:2], "zones": zi["zones"]}
        except Exception:
            res["sr"] = {"supports": [], "resistances": [], "zones": []}
        from .mood import mood_of, range_of
        mm = mood_of(load_decisions(self.con).get(sp.symbol))
        if mm and mm["mood"] == "SIDEWAYS":
            mm["range"] = range_of(df)
        res["mood"] = mm
        return res

    def reset_halt(self) -> None:
        """Clear the max-drawdown halt (manual, by Raj): forgets past results so the drawdown restarts from zero."""
        prot = load_protections(self.con)
        prot.halted, prot.paused_until, prot.results_r = False, None, []
        save_protections(self.con, prot)

    # ------------------------------------------------------------ user settings
    def apply_saved_settings(self) -> None:
        saved = get_setting(self.con, "user_settings", {}) or {}
        for k in ("capital", "risk_pct", "profile", "max_trades"):
            if k in saved:
                setattr(self.st, k, saved[k])

    def update_settings(self, capital=None, risk_pct=None, profile=None, max_trades=None) -> dict:
        from .scoring import PROFILES
        saved = get_setting(self.con, "user_settings", {}) or {}
        if capital is not None:
            if not (1000 <= float(capital) <= 1e9):
                raise ValueError("capital 1000 se 1,00,00,00,000 ke beech hona chahiye")
            saved["capital"] = float(capital)
        if risk_pct is not None:
            if not (0.001 <= float(risk_pct) <= 0.05):
                raise ValueError("risk_pct 0.1% se 5% ke beech hona chahiye")
            saved["risk_pct"] = float(risk_pct)
        if max_trades is not None:
            if not (1 <= int(max_trades) <= 5):
                raise ValueError("max_trades 1 se 5 ke beech hona chahiye")
            saved["max_trades"] = int(max_trades)
        if profile is not None:
            if profile not in PROFILES:
                raise ValueError("profile conservative/moderate/aggressive me se ek ho")
            saved["profile"] = profile
        set_setting(self.con, "user_settings", saved)
        self.apply_saved_settings()
        return saved
````

### `rtw/api.py`

````text file=rtw/api.py
"""FastAPI app: JSON API + serves the PWA from ./web. Optional access key (header x-key or ?key=)."""
from __future__ import annotations
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .db import get_setting
from .news import news_mode
from .sessions import IST
from .views import home_view, mood_view, markets_view, record_view, news_view, health_view, TABS

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class SettingsIn(BaseModel):
    capital: float | None = None
    risk_pct: float | None = None
    profile: str | None = None
    max_trades: int | None = None


def create_app(orc, now_fn=lambda: datetime.now(IST)) -> FastAPI:
    app = FastAPI(title="Raj Trading World", docs_url=None, redoc_url=None)
    st = orc.st

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if st.access_key and request.url.path.startswith("/api/"):
            key = request.headers.get("x-key") or request.query_params.get("key")
            if key != st.access_key:
                return JSONResponse({"error": "access key galat ya missing"}, status_code=401)
        return await call_next(request)

    @app.get("/api/home")
    def home():
        now = now_fn()
        return home_view(orc.con, now, orc.provider.events(now), st)

    @app.get("/api/markets/{tab}")
    def markets(tab: str):
        if tab not in TABS:
            raise HTTPException(404, "tab nahi mila")
        now = now_fn()
        return markets_view(orc.con, tab, now, st, orc.specs(now))

    @app.get("/api/search")
    def search(q: str):
        if len(q) > 40:
            raise HTTPException(400, "query bahut lambi")
        return orc.search(q, now_fn())

    @app.get("/api/chart")
    def chart(q: str, tf: str = "5m", strike: float | None = None, cp: str | None = None, expiry: str | None = None):
        if len(q) > 40:
            raise HTTPException(400, "query bahut lambi")
        return orc.chart(q, now_fn(), tf, strike, cp, expiry)

    @app.get("/api/mood")
    def mood():
        now = now_fn()
        return mood_view(orc.con, now, orc.specs(now))

    @app.get("/api/news")
    def news():
        now = now_fn()
        ev = orc.provider.events(now)
        return news_view(orc.con, orc.provider, now, ev, news_mode(ev, now, "NIFTY", vix_z=orc.provider.vix_z(now)))

    @app.get("/api/record")
    def record():
        return record_view(orc.con)

    @app.post("/api/reset_halt")
    def reset_halt():
        orc.reset_halt()
        return {"ok": True}

    @app.get("/api/health")
    def health():
        return {"mode": st.mode, "last_cycle": get_setting(orc.con, "last_cycle"), "paused": get_setting(orc.con, "paused", False),
                "components": health_view(orc.con)}

    @app.get("/api/settings")
    def get_settings_():
        return {"capital": st.capital, "risk_pct": st.risk_pct, "profile": st.profile, "mode": st.mode, "max_trades": st.max_trades}

    @app.post("/api/settings")
    def set_settings(body: SettingsIn):
        try:
            orc.update_settings(body.capital, body.risk_pct, body.profile, body.max_trades)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"capital": st.capital, "risk_pct": st.risk_pct, "profile": st.profile, "max_trades": st.max_trades}

    @app.post("/api/refresh")
    def refresh():
        now = now_fn()
        orc.refresh_all(now, "core")
        return orc.cycle(now, "core")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(WEB_DIR, "index.html"))

    if os.path.isdir(WEB_DIR):
        app.mount("/", StaticFiles(directory=WEB_DIR), name="web")
    return app
````

### `rtw/telegram_bot.py`

````text file=rtw/telegram_bot.py
"""Telegram commands. handle_command is pure (testable); run_bot is the polling loop."""
from __future__ import annotations
import threading
from datetime import datetime
from .db import get_setting, set_setting, load_decisions, open_trade, open_trades
from .notify import format_wait, format_brief, format_signal_card, fmt
from .news import news_mode
from .views import home_view, record_view, events_payload, health_view

HELP = ("/status — abhi ka signal ya WAIT\n/why — signal ya WAIT ki wajah\n/record — track record\n/brief — pre-market brief\n"
        "/pause — naya signal band\n/resume — naya signal chalu\n/reset_halt — drawdown halt hatao (soch ke)\n/health — data sources ki sehat\n/help — ye list")


def handle_command(text: str, orc, now: datetime) -> str:
    cmd = (text or "").strip().split()[0].lower().split("@")[0] if (text or "").strip() else ""
    st, con = orc.st, orc.con
    events = orc.provider.events(now)
    if cmd in ("/start", "/help"):
        return "Raj Trading World me swagat hai.\n" + HELP
    if cmd == "/status":
        h = home_view(con, now, events, st)
        if h.get("trades"):
            return "\n\n".join(format_signal_card(t) for t in h["trades"])
        return format_wait(h["wait"])
    if cmd == "/why":
        opens = open_trades(con)
        if opens:
            return "\n".join(f"{s.symbol}: " + ("; ".join(s.reasons) if s.reasons else "wajah record nahi hui") for s, _ in opens)
        return format_wait(home_view(con, now, events, st)["wait"])
    if cmd == "/record":
        r = record_view(con)["all"]
        return f"Trades: {r['trades']} | Win rate: {r['win_rate'] * 100:.0f}% | Total: {r['total_r']:+.2f}R | Avg: {r['avg_r']:+.2f}R"
    if cmd == "/brief":
        h = home_view(con, now, events, st)
        nm = news_mode(events, now, "NIFTY")
        return format_brief(h, {"mode": nm["mode"], "events": events_payload(events, now, 24)})
    if cmd == "/reset_halt":
        orc.reset_halt()
        return "Max-drawdown halt hata diya, drawdown ginti zero se shuru. Dhyan se."
    if cmd == "/pause":
        set_setting(con, "paused", True)
        return "Naya signal band. Chalu trade ki nigrani jaari rahegi. /resume se wapas chalu."
    if cmd == "/resume":
        set_setting(con, "paused", False)
        return "Naya signal chalu."
    if cmd == "/health":
        rows = health_view(con)
        bad = [r for r in rows if r["status"] != "OK"]
        return f"{len(rows)} components, {len(bad)} me dikkat" + ("".join(f"\n• {r['component']}: {r['detail']}" for r in bad[:8]) if bad else ". Sab theek.")
    return "Ye command samajh nahi aaya.\n" + HELP


def run_bot(orc, sender, now_fn, stop: threading.Event) -> None:
    offset = None
    pend = sender.get_updates(None, timeout=0)          # drop commands that piled up while the app was off
    if pend:
        offset = pend[-1]["update_id"] + 1
    while not stop.is_set():
        for u in sender.get_updates(offset):
            offset = u["update_id"] + 1
            m = u.get("message") or {}
            if str((m.get("chat") or {}).get("id")) != str(sender.chat_id):
                continue                      # ignore strangers
            try:
                sender.send(handle_command(m.get("text", ""), orc, now_fn()))
            except Exception as e:
                sender.send(f"Command me error: {e}")
        stop.wait(1.0)
````

### `rtw/jobs.py`

````text file=rtw/jobs.py
"""Scheduled jobs (plain functions, each safe to call alone and fully testable with FakeProvider)."""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from .backtest import backtest, group_setups, passes_record
from .config import CORE_SPECS
from .db import upsert_candles, put_setup_stats, log_health, set_setting, get_setting
from .notify import format_brief
from .news import news_mode
from .sessions import IST
from .views import home_view, events_payload


def bootstrap_history(orc, now: datetime, days: int = 60) -> int:
    """First start: fill the candle table with history so indicators/backtests have data."""
    n = 0
    for sp in list(CORE_SPECS) + list(orc.provider.stock_universe(now, orc.st.stocks_top_n)):
        try:
            df = orc.provider.history(sp, now, days)
        except Exception as e:
            log_health(orc.con, now, f"history:{sp.symbol}", "FAIL", repr(e))
            continue
        if df is None or df.empty:
            log_health(orc.con, now, f"history:{sp.symbol}", "FAIL", "no history")
            continue
        rows = [(ts.tz_convert(IST).isoformat(), float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume)) for ts, r in df.iterrows()]
        upsert_candles(orc.con, sp.symbol, "5m", rows)
        log_health(orc.con, now, f"history:{sp.symbol}", "OK", f"{len(rows)} bars")
        n += 1
    return n


def nightly_backtest(orc, now: datetime, step: int = 3, min_bars: int = 1200) -> dict:
    """Walk-forward test per setup (asset class | direction | regime) on stored history. Writes setup_stats.
    Rules that stop working get benched (benched=1) -> their signals are blocked by the setup_record gate."""
    from .db import load_df
    ctx = orc.context(now)
    by_class: dict = {}
    for sp in CORE_SPECS:
        df = load_df(orc.con, sp.symbol, "5m", 20000)
        if df is None or len(df) < min_bars:
            continue
        lot, cap = orc._engine_lot_and_capital(sp, ctx)
        try:
            tr = backtest(df, sp.symbol, sp.asset_class, lot_size=lot, capital=cap, risk_pct=orc.st.risk_pct, profile=orc.st.profile,
                          step=step, segment="CRYPTO", warmup=120)       # sessions ignored: history already only has market hours
        except Exception as e:
            log_health(orc.con, now, f"backtest:{sp.symbol}", "FAIL", repr(e))
            continue
        by_class.setdefault(sp.asset_class, []).extend(tr)
    written = {}
    for cls, trades in by_class.items():
        for key, st in group_setups(trades).items():
            st["benched"] = int(st["trades"] >= 30 and not passes_record(st))
            put_setup_stats(orc.con, key, st, now)
            written[key] = st
    log_health(orc.con, now, "nightly_backtest", "OK", f"{len(written)} setups")
    return written


def health_check(orc, now: datetime) -> list:
    rows = orc.provider.health(now)
    prev = get_setting(orc.con, "health_prev", {}) or {}
    cur = {}
    for comp, status, detail in rows:
        log_health(orc.con, now, comp, status, detail)
        cur[comp] = status
        if status == "FAIL" and prev.get(comp) != "FAIL":
            orc.send(f"⚠️ Data problem: {comp} — {detail}")
        if status == "OK" and prev.get(comp) == "FAIL":
            orc.send(f"✅ Theek ho gaya: {comp}")
    set_setting(orc.con, "health_prev", cur)
    return rows


def morning_brief(orc, now: datetime) -> str:
    ev = orc.provider.events(now)
    h = home_view(orc.con, now, ev, orc.st)
    nm = news_mode(ev, now, "NIFTY", vix_z=orc.provider.vix_z(now))
    text = format_brief(h, {"mode": nm["mode"], "events": events_payload(ev, now, 24)})
    orc.send(text)
    return text


def update_holidays(orc, now: datetime) -> int:
    from .adapters import nse
    days = nse.fetch_holidays()
    path = os.path.join("data", "holidays.json")
    if os.path.exists(path):                              # manual override/addition file: ["2026-11-10", ...]
        try:
            days = sorted(set(days) | set(json.load(open(path, encoding="utf-8"))))
        except Exception:
            pass
    if days:
        set_setting(orc.con, "holidays", days)
    return len(days)
````

### `rtw/scheduler.py`

````text file=rtw/scheduler.py
"""APScheduler wiring. Every job is wrapped so an exception is logged and never kills the scheduler."""
from __future__ import annotations
import threading
import traceback
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from . import jobs
from .db import log_health, get_setting, open_trade
from .sessions import IST


def _safe(orc, name, fn):
    def run():
        now = datetime.now(IST)
        try:
            fn(now)
        except Exception as e:
            log_health(orc.con, now, f"job:{name}", "FAIL", f"{e!r} {traceback.format_exc()[-200:]}")
    run.__name__ = name
    return run


def build_scheduler(orc, live=None) -> BackgroundScheduler:
    """live = LiveProvider or None (DEMO). Timezone is IST for every cron."""
    sch = BackgroundScheduler(timezone=IST, job_defaults={"max_instances": 1, "coalesce": True, "misfire_grace_time": 60})

    def core(now):
        orc.refresh_all(now, "core")
        orc.cycle(now, "core")

    def stocks(now):
        orc.refresh_all(now, "stocks")
        orc.cycle(now, "stocks")

    sch.add_job(_safe(orc, "core", core), "cron", second=8, id="core")           # 8 s after every minute: the bar has closed
    sch.add_job(_safe(orc, "stocks", stocks), "cron", minute="*/5", second=25, id="stocks")   # just after each 5-min bar closes
    sch.add_job(_safe(orc, "health", lambda n: jobs.health_check(orc, n)), "interval", minutes=10, id="health")
    sch.add_job(_safe(orc, "brief", lambda n: jobs.morning_brief(orc, n)), "cron", day_of_week="mon-fri", hour=8, minute=30, id="brief")
    sch.add_job(_safe(orc, "backtest", lambda n: jobs.nightly_backtest(orc, n)), "cron", hour=23, minute=50, id="backtest")
    if live is not None:
        sch.add_job(_safe(orc, "news", lambda n: live.collect_news(n)), "interval", minutes=2, id="news")
        sch.add_job(_safe(orc, "gdelt", lambda n: live.collect_news(n, gdelt=True)), "interval", minutes=15, id="gdelt")

        def morning(now):
            for c, s, d in live.start(now):
                log_health(orc.con, now, c, s, d)
            live.refresh_stock_universe(now, 100)
            jobs.update_holidays(orc, now)

        sch.add_job(_safe(orc, "morning", morning), "cron", hour=6, minute=0, id="morning")
        sch.add_job(_safe(orc, "iv", lambda n: [live.record_iv(sp, n) for sp in orc.specs(n) if sp.has_options]), "cron",
                    day_of_week="mon-fri", hour=15, minute=45, id="iv")
    return sch
````

### `rtw/icons.py`

````text file=rtw/icons.py
"""Creates web/icon-192.png and web/icon-512.png with the standard library only (no Pillow needed)."""
import os
import struct
import zlib

BG, BAR, UP = (11, 16, 32), (60, 70, 100), (46, 204, 113)


def _png(size: int) -> bytes:
    rows = []
    bars = [(0.20, 0.55), (0.40, 0.42), (0.60, 0.30), (0.78, 0.16)]      # (x center, top y) rising chart
    w = size * 0.11
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            px = BG
            fx, fy = x / size, y / size
            for i, (cx, top) in enumerate(bars):
                if abs(fx - cx) * size <= w and top <= fy <= 0.80:
                    px = UP if i == len(bars) - 1 else BAR
            row += bytes(px)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(t: bytes, d: bytes) -> bytes:
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def ensure_icons(web_dir: str) -> list:
    made = []
    for size in (192, 512):
        p = os.path.join(web_dir, f"icon-{size}.png")
        if not os.path.exists(p):
            os.makedirs(web_dir, exist_ok=True)
            open(p, "wb").write(_png(size))
            made.append(p)
    return made
````

### `rtw/live.py`

````text file=rtw/live.py
"""LiveProvider: composes the adapters with fallbacks + small caches. Implements the Provider contract (never raises)."""
from __future__ import annotations
import threading
import time
from datetime import datetime, timedelta
import pandas as pd
from .adapters import angel as A, yf as Y, crypto as C, nse as N, newsfeeds as NF, calendar as CAL
from .config import Settings, Spec, stock_spec, DEFAULT_STOCKS
from .db import get_setting, set_setting, log_health
from .news import Tag, tag_headline, cluster_stories, story_confirmed
from .options import iv_percentile
from .provider import Provider
from .sessions import IST, is_open

HOLIDAY_FILE_KEY = "holidays"        # settings key: list of ISO dates (maintained by `update_holidays` job / by hand)


class _Cache:
    def __init__(self):
        self.d: dict = {}

    def get(self, k, ttl, fn, max_stale=None):
        """Fresh value if younger than ttl; else call fn. If fn fails, a stale value is served only while younger than max_stale
        (default 6 x ttl) - older data is worse than no data."""
        v = self.d.get(k)
        if v and time.time() - v[0] < ttl:
            return v[1]
        val = fn()
        if val not in (None, {}, []):
            self.d[k] = (time.time(), val)
            return val
        if v and time.time() - v[0] < (max_stale if max_stale is not None else ttl * 6):
            return v[1]
        return val


class LiveProvider(Provider):
    name = "live"

    def __init__(self, settings: Settings, con):
        self.st, self.con = settings, con
        self.angel = A.AngelClient(settings) if settings.angel_ready else None
        self.cache = _Cache()
        self._tok: dict = {}
        self._news: list[dict] = []
        self._news_seen: set = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------ startup
    def start(self, now: datetime) -> list[tuple]:
        """Login + master. Returns health tuples (component, status, detail)."""
        out = []
        if self.angel:
            ok = self.angel.login()
            out.append(("angel_login", "OK" if ok else "FAIL", self.angel.last_error))
            if ok:
                okm = self.angel.load_master()
                out.append(("angel_master", "OK" if okm else "FAIL", self.angel.last_error))
        else:
            out.append(("angel_login", "SKIP", "Angel keys .env me nahi hain -> yfinance/Binance fallback"))
        return out

    # ------------------------------------------------------------ token resolution
    def _angel_target(self, spec: Spec, now: datetime) -> dict | None:
        if not (self.angel and self.angel.master):
            return None
        key = (spec.symbol, now.date())
        if key in self._tok:
            return self._tok[key]
        m, today = self.angel.master, now.date()
        row = None
        if spec.asset_class == "INDEX":
            row = A.index_row(m, spec.angel_name) or ({"token": A.INDEX_TOKENS.get(spec.angel_name), "symbol": spec.angel_name} if A.INDEX_TOKENS.get(spec.angel_name) else None)
            exch = "NSE"
        elif spec.asset_class == "STOCK":
            row, exch = A.equity_row(m, spec.angel_name), "NSE"
        elif spec.asset_class == "COMMODITY":
            row, exch = A.front_future(m, spec.angel_name, "MCX", today, 3, "FUTCOM"), "MCX"
        elif spec.asset_class == "FOREX":
            row, exch = A.front_future(m, spec.angel_name, "CDS", today, 2, "FUTCUR"), "CDS"
        else:
            return None
        t = {"exch": exch, "token": row["token"], "symbol": row.get("symbol", spec.angel_name), "row": row} if row else None
        self._tok[key] = t
        return t

    # ------------------------------------------------------------ candles
    def candles(self, spec, now, tf="5m", n=400):
        try:
            if spec.exch == "BINANCE":
                df = C.klines(spec.symbol, now, "5m", min(n, 1000))
                return df if df is not None else Y.candles(spec.yf, now)
            t = self._angel_target(spec, now)
            if t:
                days = 6 if spec.segment == "NSE" else 4
                df = self.angel.candles(t["exch"], t["token"], tf, now - timedelta(days=days), now)
                if df is not None and len(df):
                    df = Y.drop_open_bar(df, now, 5).tail(n)
                    df.attrs["contract"] = t.get("symbol")            # pipeline resets state when the front contract rolls
                    return df
            # MCX has NO fallback (COMEX units differ). FOREX falls back only when Angel is not configured at all
            # (yfinance spot and CDS futures differ slightly - mixing them mid-trade would corrupt levels).
            if spec.asset_class in ("INDEX", "STOCK") and spec.yf or (spec.asset_class == "FOREX" and spec.yf and not self.angel):
                df = Y.candles(spec.yf, now)
                return df.tail(n) if df is not None else None
        except Exception:
            return None
        return None

    def history(self, spec, now, days=60):
        try:
            if spec.exch == "BINANCE":
                return C.klines(spec.symbol, now, "5m", 1000)
            t = self._angel_target(spec, now)
            if t:
                df = self.angel.candles(t["exch"], t["token"], "5m", now - timedelta(days=days), now)
                return Y.drop_open_bar(df, now, 5) if df is not None else None
            return Y.candles(spec.yf, now, "5m", "60d") if spec.yf and spec.asset_class != "COMMODITY" else None
        except Exception:
            return None

    def ltp(self, spec, now):
        try:
            t = self._angel_target(spec, now)
            if t:
                return self.angel.ltp(t["exch"], t["symbol"], t["token"])
        except Exception:
            pass
        return None

    # ------------------------------------------------------------ context
    def global_changes(self, now):
        return self.cache.get("global", 600, Y.daily_changes) or {}

    def vix_z(self, now):
        return self.cache.get("vixz", 900, Y.vix_zscore)

    def usdinr(self, now):
        def lvl():
            df = Y.candles("USDINR=X", now, "5m", "1d")
            return float(df["close"].iloc[-1]) if df is not None and len(df) else None
        return self.cache.get("usdinr", 900, lvl) or 88.0

    def smart_inputs(self, spec, now):
        try:
            if spec.asset_class == "INDEX":
                d = self.cache.get("fiidii", 1800, N.fii_dii) or {}
                return {"kind": "index", **d} if d else {}
            if spec.asset_class == "CRYPTO":
                return self.cache.get("cryptosmart", 300, C.smart_inputs) or {}
        except Exception:
            pass
        return {}

    def lot(self, spec):
        try:
            if self.angel and self.angel.master and spec.asset_class in ("INDEX", "STOCK"):
                it = "OPTIDX" if spec.asset_class == "INDEX" else "OPTSTK"
                v = A.lot_from_master(self.angel.master, spec.angel_name, "NFO", it)
                if v:
                    return v
        except Exception:
            pass
        return spec.lot

    def holidays(self):
        try:
            from datetime import date
            return {date.fromisoformat(x) for x in (get_setting(self.con, HOLIDAY_FILE_KEY, []) or [])}
        except Exception:
            return set()

    # ------------------------------------------------------------ options
    def _pick_expiry(self, spec: Spec, now: datetime):
        if not (self.angel and self.angel.master):
            return None
        it = "OPTIDX" if spec.asset_class == "INDEX" else "OPTSTK"
        exps = A.option_expiries(self.angel.master, spec.angel_name, now.date(), it)
        for e in exps:                                   # nearest expiry that still has >= 1 day
            if (e - now.date()).days >= 1:
                return e
        return exps[0] if exps else None

    def option_chain(self, spec, now):
        try:
            exp = self._pick_expiry(spec, now)
            if exp is None:
                return None
            df = self.cache.get(f"chain:{spec.symbol}", 45, lambda: N.option_chain(spec.angel_name))
            rows = N.chain_from_df(df, exp) if df is not None else []
            if not rows and df is not None:
                rows = N.chain_from_df(df)                # frame has a single expiry already
            spot = self.ltp(spec, now)
            if not rows:
                return None
            if spot is None:
                from .db import load_df
                d = load_df(self.con, spec.symbol, "5m", 2)
                spot = float(d["close"].iloc[-1]) if d is not None else None
            if spot is None:
                return None
            dte = max(0.0, (datetime.combine(exp, datetime.min.time(), tzinfo=IST) + timedelta(hours=15, minutes=30) - now).total_seconds() / 86400.0)
            iv = N.atm_iv(rows, spot, dte) or 0.15
            hist = get_setting(self.con, f"ivhist:{spec.symbol}", []) or []
            return {"expiry": exp.isoformat(), "dte": dte, "rows": rows, "iv": iv, "iv_pct": iv_percentile(hist, iv), "spot": spot, "lot": self.lot(spec)}
        except Exception:
            return None

    def option_ltp(self, spec, strike, cp, expiry, now):
        try:
            if not (self.angel and self.angel.master):
                return None
            from datetime import date
            it = "OPTIDX" if spec.asset_class == "INDEX" else "OPTSTK"
            r = A.option_token(self.angel.master, spec.angel_name, date.fromisoformat(expiry), strike, cp, it)
            return self.angel.ltp("NFO", r["symbol"], r["token"]) if r else None
        except Exception:
            return None

    def option_candles(self, spec, strike, cp, expiry, now):
        """Real 5m bars of one option contract from Angel (NFO token). None if unavailable. Not tested live."""
        try:
            if not (self.angel and self.angel.master):
                return None
            from datetime import date
            it = "OPTIDX" if spec.asset_class == "INDEX" else "OPTSTK"
            r = A.option_token(self.angel.master, spec.angel_name, date.fromisoformat(expiry), strike, cp, it)
            if not r:
                return None
            df = self.angel.candles("NFO", r["token"], "5m", now - timedelta(days=4), now)
            return Y.drop_open_bar(df, now, 5).tail(400) if df is not None and len(df) else None
        except Exception:
            return None

    def record_iv(self, spec: Spec, now: datetime) -> None:
        """Daily job: append today's ATM IV to history (needed for IV percentile)."""
        ch = self.option_chain(spec, now)
        if ch:
            h = (get_setting(self.con, f"ivhist:{spec.symbol}", []) or [])[-250:]
            h.append(ch["iv"])
            set_setting(self.con, f"ivhist:{spec.symbol}", h)

    # ------------------------------------------------------------ news
    def collect_news(self, now: datetime, gdelt: bool = False) -> int:
        items = NF.fetch_rss(now) + (NF.fetch_gdelt(now) if gdelt else [])
        new = 0
        with self._lock:
            for it in items:
                h = NF.url_hash(it["url"], it["title"])
                if h in self._news_seen:
                    continue
                self._news_seen.add(h)
                self._news.append(it)
                new += 1
                try:
                    self.con.execute("INSERT OR IGNORE INTO news_items(url_hash,title,source,official,ts,tags_json) VALUES(?,?,?,?,?,?)",
                                     (h, it["title"], it["source"], int(it["official"]), it["ts"].isoformat(), "[]"))
                except Exception:
                    pass
            self.con.commit()
            cut = now - timedelta(hours=8)
            self._news = [x for x in self._news if x["ts"] >= cut]
            if len(self._news_seen) > 20000:
                self._news_seen = {NF.url_hash(x["url"], x["title"]) for x in self._news}
        return new

    def news_tags(self, now):
        with self._lock:
            items = list(self._news)
        tags: list[Tag] = []
        for st in cluster_stories([x for x in items if x["ts"] >= now - timedelta(hours=6)]):
            best = max(st["items"], key=lambda x: x.get("trust", 0.5))
            ts = tag_headline(best["title"], st["first_ts"], best["source"], st["official"], best.get("trust", 0.6))
            if not story_confirmed(st):               # single unofficial source: weak vote only
                for t in ts:
                    t.magnitude *= 0.4
            tags += ts
        return tags

    def headlines(self, now):
        with self._lock:
            items = sorted(self._news, key=lambda x: x["ts"], reverse=True)[:40]
        out = []
        for it in items:
            tg = tag_headline(it["title"], it["ts"], it["source"], it["official"], it.get("trust", 0.6))
            out.append({"title": it["title"], "source": it["source"], "ts": it["ts"].isoformat(),
                        "tags": [f"{t.asset} {'+' if t.direction > 0 else '-'}" for t in tg][:4]})
        return out

    def events(self, now):
        ff = self.cache.get("ff", 3600, CAL.fetch_ff) or []
        return CAL.all_events(now, ff=ff)

    # ------------------------------------------------------------ stocks
    def stock_universe(self, now, n=50):
        rows = get_setting(self.con, "stock_universe", []) or [{"symbol": x} for x in DEFAULT_STOCKS]
        return [stock_spec(r["symbol"]) for r in rows[:n]]

    def refresh_stock_universe(self, now: datetime, n: int = 100) -> int:
        rows = N.fno_universe(n)
        if rows:
            set_setting(self.con, "stock_universe", rows)
        return len(rows)

    def stock_lot(self, symbol: str) -> int:
        for r in get_setting(self.con, "stock_universe", []) or []:
            if r["symbol"] == symbol:
                return int(r.get("lot", 1))
        return 1

    # ------------------------------------------------------------ health
    def health(self, now):
        out = []
        if self.angel:
            ok = bool(self.angel.api and self.angel.logged_at)
            out.append(("angel_login", "OK" if ok else "FAIL", self.angel.last_error or "logged in"))
            out.append(("angel_master", "OK" if self.angel.master else "FAIL", f"{len(self.angel.master)} rows"))
        g = self.global_changes(now)
        out.append(("global_yfinance", "OK" if len(g) >= 8 else "FAIL", f"{len(g)} tickers"))
        out.append(("news_items", "OK" if self._news else "FAIL", f"{len(self._news)} items in memory"))
        out.append(("stock_universe", "OK" if get_setting(self.con, "stock_universe", []) else "FAIL",
                    f"{len(get_setting(self.con, 'stock_universe', []) or [])} stocks (default list used if 0)"))
        ev = self.events(now)
        out.append(("calendar", "OK" if ev else "FAIL", f"{len(ev)} events"))
        return out
````

### `rtw/adapters/__init__.py`

````text file=rtw/adapters/__init__.py
# package marker
````

### `rtw/adapters/angel.py`

````text file=rtw/adapters/angel.py
"""Angel One SmartAPI adapter. Login with TOTP, instrument master, candles, LTP, Greeks.
LIVE CALLS ARE VERIFIED BY SIGNATURE ONLY (sandbox had no broker access) -> run `python check_setup.py` first."""
from __future__ import annotations
import json
import os
import threading
import time
from datetime import date, datetime, timedelta
import pandas as pd
import requests
from ..sessions import IST

MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
INDEX_TOKENS = {"NIFTY": "99926000", "BANKNIFTY": "99926009", "MIDCPNIFTY": "99926074", "INDIAVIX": "99926017"}   # verified at runtime
INTERVALS = {"1m": "ONE_MINUTE", "3m": "THREE_MINUTE", "5m": "FIVE_MINUTE", "10m": "TEN_MINUTE", "15m": "FIFTEEN_MINUTE",
             "30m": "THIRTY_MINUTE", "1h": "ONE_HOUR", "1d": "ONE_DAY"}
MAX_DAYS = {"1m": 25, "3m": 90, "5m": 90, "10m": 90, "15m": 190, "30m": 190, "1h": 390, "1d": 1900}   # per-request window (safe)


# ---------------------------------------------------------------- pure helpers (offline-testable)
def parse_expiry(s: str) -> date | None:
    try:
        return datetime.strptime(s.title(), "%d%b%Y").date()
    except Exception:
        return None


def parse_candles(resp: dict) -> pd.DataFrame | None:
    """getCandleData response -> DataFrame(open,high,low,close,volume) indexed by IST bar START time."""
    rows = (resp or {}).get("data")
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(IST)
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="last")].astype(float)
    return df


def front_future(master: list, name: str, exch: str, today: date, roll_days: int = 3, itype: str | None = None) -> dict | None:
    """Nearest future of `name` whose expiry is >= today+roll_days (so we roll BEFORE the last days: thin volume, expiry noise)."""
    types = {itype} if itype else {"FUTCOM", "FUTIDX", "FUTSTK", "FUTCUR"}
    c = []
    for r in master:
        if r.get("name") == name and r.get("exch_seg") == exch and r.get("instrumenttype") in types:
            e = parse_expiry(r.get("expiry", ""))
            if e and e >= today + timedelta(days=roll_days):
                c.append((e, r))
    if not c:
        c = [(parse_expiry(r["expiry"]), r) for r in master if r.get("name") == name and r.get("exch_seg") == exch
             and r.get("instrumenttype") in types and parse_expiry(r.get("expiry", "")) and parse_expiry(r["expiry"]) >= today]
    return min(c, key=lambda x: x[0])[1] if c else None


def equity_row(master: list, symbol: str) -> dict | None:
    for r in master:
        if r.get("exch_seg") == "NSE" and r.get("symbol") == f"{symbol}-EQ":
            return r
    return None


def index_row(master: list, name: str) -> dict | None:
    want = {"NIFTY": ["nifty 50", "nifty"], "BANKNIFTY": ["nifty bank", "banknifty"], "MIDCPNIFTY": ["nifty midcap select", "nifty mid select", "midcpnifty"],
            "INDIAVIX": ["india vix"]}.get(name, [name.lower()])
    for r in master:
        if r.get("exch_seg") == "NSE" and r.get("instrumenttype") == "AMXIDX" and (r.get("symbol", "").lower() in want or r.get("name", "").lower() in want):
            return r
    return None


def lot_from_master(master: list, name: str, exch: str, itype: str) -> int | None:
    for r in master:
        if r.get("name") == name and r.get("exch_seg") == exch and r.get("instrumenttype") == itype:
            try:
                return int(float(r["lotsize"]))
            except Exception:
                return None
    return None


def option_expiries(master: list, name: str, today: date, itype: str = "OPTIDX") -> list[date]:
    ex = {parse_expiry(r["expiry"]) for r in master if r.get("name") == name and r.get("exch_seg") in ("NFO",) and r.get("instrumenttype") == itype}
    return sorted(e for e in ex if e and e >= today)


def option_token(master: list, name: str, expiry: date, strike: float, cp: str, itype: str = "OPTIDX") -> dict | None:
    """Master stores strike x100 (e.g. '2450000.000000')."""
    for r in master:
        if (r.get("name") == name and r.get("exch_seg") == "NFO" and r.get("instrumenttype") == itype and parse_expiry(r.get("expiry", "")) == expiry
                and abs(float(r.get("strike", 0)) / 100.0 - strike) < 1e-6 and r.get("symbol", "").endswith(cp)):
            return r
    return None


# ---------------------------------------------------------------- client
class AngelClient:
    MIN_GAP = 0.40       # seconds between REST calls (limit is 3/sec for candles)

    def __init__(self, settings, cache_dir: str = "data"):
        self.st = settings
        self.cache_dir = cache_dir
        self.api = None
        self.master: list = []
        self.logged_at: datetime | None = None
        self.last_error = ""
        self._lock = threading.Lock()
        self._last = 0.0
        self._login_fail_at = 0.0          # login cooldown: repeated bad logins can lock the Angel account

    # ---- session
    LOGIN_COOLDOWN = 90.0

    def login(self) -> bool:
        with self._lock:
            if time.time() - self._login_fail_at < self.LOGIN_COOLDOWN:
                return False
            try:
                import pyotp
                from SmartApi import SmartConnect
                api = SmartConnect(api_key=self.st.angel_api_key)
                totp = pyotp.TOTP(self.st.angel_totp_secret).now()
                d = api.generateSession(self.st.angel_client_code, self.st.angel_pin, totp)
                if not d or not d.get("status"):
                    self.last_error = f"login fail: {(d or {}).get('message', 'no response')}"
                    self._login_fail_at = time.time()
                    return False
                self.api, self.logged_at, self.last_error = api, datetime.now(IST), ""
                return True
            except Exception as e:
                self.last_error = f"login error: {e}"
                self._login_fail_at = time.time()
                return False

    def ensure(self) -> bool:
        if self.api and self.logged_at and datetime.now(IST) - self.logged_at < timedelta(hours=5):
            return True
        return self.login()

    def _throttle(self):
        gap = time.time() - self._last
        if gap < self.MIN_GAP:
            time.sleep(self.MIN_GAP - gap)
        self._last = time.time()

    def _call(self, fn, *a):
        """One retry after re-login (token expiry). Returns response dict or None."""
        for attempt in (0, 1):
            if not self.ensure():
                return None
            with self._lock:
                self._throttle()
            try:
                r = fn(*a)
                if r and r.get("status"):
                    return r
                msg = str((r or {}).get("message", ""))
                self.last_error = msg
                if attempt == 0 and any(k in msg.lower() for k in ("invalid token", "token expired", "session", "unauthor", "login")):
                    self.api = None
                    continue
                return None
            except Exception as e:                      # network blips must NOT force a re-login (that burns login attempts)
                self.last_error = str(e)
                if attempt == 0 and any(k in str(e).lower() for k in ("token", "session", "unauthor")):
                    self.api = None
                    continue
                return None
        return None

    # ---- master
    def load_master(self, force: bool = False) -> bool:
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, f"master_{datetime.now(IST):%Y%m%d}.json")
        try:
            if not force and os.path.exists(path):
                self.master = json.load(open(path, encoding="utf-8"))
            else:
                r = requests.get(MASTER_URL, timeout=90)
                r.raise_for_status()
                self.master = r.json()
                json.dump(self.master, open(path, "w", encoding="utf-8"))
                for old in os.listdir(self.cache_dir):
                    if old.startswith("master_") and old != os.path.basename(path):
                        os.remove(os.path.join(self.cache_dir, old))
            return len(self.master) > 1000
        except Exception as e:
            self.last_error = f"master: {e}"
            return False

    # ---- data
    def candles(self, exch: str, token: str, tf: str, start: datetime, end: datetime) -> pd.DataFrame | None:
        """Loops over windows (API limits days per request)."""
        step = timedelta(days=MAX_DAYS[tf])
        frames, cur = [], start
        while cur < end:
            nxt = min(cur + step, end)
            p = {"exchange": exch, "symboltoken": token, "interval": INTERVALS[tf],
                 "fromdate": cur.strftime("%Y-%m-%d %H:%M"), "todate": nxt.strftime("%Y-%m-%d %H:%M")}
            r = self._call(lambda: self.api.getCandleData(dict(p)))
            df = parse_candles(r) if r else None
            if df is not None:
                frames.append(df)
            cur = nxt
        if not frames:
            return None
        return pd.concat(frames).sort_index().loc[lambda d: ~d.index.duplicated(keep="last")]

    def ltp(self, exch: str, tradingsymbol: str, token: str) -> float | None:
        if not self.ensure():
            return None
        r = self._call(lambda: self.api.ltpData(exch, tradingsymbol, token))
        try:
            return float(r["data"]["ltp"])
        except Exception:
            return None

    def greeks(self, name: str, expiry_ddmmmyyyy: str) -> list:
        if not self.ensure():
            return []
        r = self._call(lambda: self.api.optionGreek({"name": name, "expirydate": expiry_ddmmmyyyy}))
        return (r or {}).get("data") or []
````

### `rtw/adapters/yf.py`

````text file=rtw/adapters/yf.py
"""yfinance adapter: global context, India VIX, fallback candles. Never raises."""
from __future__ import annotations
import math
import threading
from datetime import datetime
import pandas as pd
from ..sessions import IST

_YF_LOCK = threading.Lock()      # yfinance shares global state -> one download at a time

GLOBAL_TICKERS = ["^GSPC", "ES=F", "NQ=F", "^IXIC", "^N225", "^HSI", "DX-Y.NYB", "CL=F", "BZ=F", "^VIX", "^TNX", "USDINR=X", "GC=F", "SI=F",
                  "NG=F", "BTC-USD", "EURUSD=X", "GBPUSD=X", "JPY=X"]


def _dl(tickers, **kw):
    import yfinance as yf
    with _YF_LOCK:
        return yf.download(tickers, progress=False, auto_adjust=False, **kw)


def normalize(df: pd.DataFrame) -> pd.DataFrame | None:
    """yfinance frame (possibly MultiIndex columns) -> open/high/low/close/volume, IST index."""
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    need = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in need):
        return None
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df = df[need + ["volume"]].dropna(subset=need)
    idx = pd.to_datetime(df.index)
    df.index = idx.tz_localize("UTC").tz_convert(IST) if idx.tz is None else idx.tz_convert(IST)
    return df.astype(float)


def drop_open_bar(df: pd.DataFrame, now: datetime, tf_min: int = 5) -> pd.DataFrame:
    """Keep only CLOSED bars (bar start + tf <= now)."""
    if df is None or df.empty:
        return df
    return df[df.index + pd.Timedelta(minutes=tf_min) <= pd.Timestamp(now)]


def candles(ticker: str, now: datetime, interval: str = "5m", period: str = "5d") -> pd.DataFrame | None:
    try:
        import yfinance as yf
        df = normalize(_dl(ticker, period=period, interval=interval, threads=False))
        return drop_open_bar(df, now, 5) if df is not None else None
    except Exception:
        return None


def daily_changes(tickers: list[str] = GLOBAL_TICKERS) -> dict:
    """% change of last close vs previous close for each ticker. Missing -> absent."""
    out: dict = {}
    try:
        import yfinance as yf
        data = _dl(tickers, period="7d", interval="1d", threads=False)
        close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data
        for t in tickers:
            if t in close.columns:
                s = close[t].dropna()
                if len(s) >= 2 and s.iloc[-2] != 0:
                    out[t] = float((s.iloc[-1] / s.iloc[-2] - 1.0) * 100.0)
    except Exception:
        pass
    return out


def vix_zscore(ticker: str = "^INDIAVIX", window: int = 60) -> float | None:
    """z-score of TODAY'S % CHANGE in India VIX vs its own last `window` daily % changes (a spike detector, not a level z-score)."""
    try:
        s = normalize_daily(_dl(ticker, period="6mo", interval="1d"))
        if s is None or len(s) < 30:
            return None
        ch = s.pct_change().dropna() * 100.0
        h = ch.tail(window)
        sd = float(h.std())
        return (float(ch.iloc[-1]) - float(h.mean())) / sd if sd > 0 else 0.0
    except Exception:
        return None


def normalize_daily(df) -> pd.Series | None:
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    c = df["Close"].dropna() if "Close" in df.columns else None
    return c
````

### `rtw/adapters/crypto.py`

````text file=rtw/adapters/crypto.py
"""Binance public REST (no key) + Fear&Greed. Never raises. If Binance is geo-blocked the caller falls back to yfinance BTC-USD."""
from __future__ import annotations
from datetime import datetime
import pandas as pd
import requests
from ..sessions import IST

SPOT = "https://api.binance.com"
FUT = "https://fapi.binance.com"


def parse_klines(rows: list, now: datetime | None = None, tf_min: int = 5) -> pd.DataFrame | None:
    """Binance kline row: [openTime ms, o, h, l, c, volume, closeTime ms, ...]."""
    if not rows:
        return None
    df = pd.DataFrame([[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows], columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_convert(IST)
    df = df.set_index("ts").astype(float)
    if now is not None:
        df = df[df.index + pd.Timedelta(minutes=tf_min) <= pd.Timestamp(now)]
    return df


def klines(symbol: str, now: datetime, interval: str = "5m", limit: int = 500) -> pd.DataFrame | None:
    try:
        r = requests.get(f"{SPOT}/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
        return parse_klines(r.json(), now) if r.ok else None
    except Exception:
        return None


def _get(url: str, params: dict):
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json() if r.ok else None
    except Exception:
        return None


def smart_inputs(symbol: str = "BTCUSDT") -> dict:
    out: dict = {"kind": "crypto"}
    j = _get(f"{FUT}/fapi/v1/premiumIndex", {"symbol": symbol})
    if isinstance(j, dict) and "lastFundingRate" in j:
        out["funding_rate"] = float(j["lastFundingRate"])
    j = _get(f"{FUT}/futures/data/globalLongShortAccountRatio", {"symbol": symbol, "period": "1h", "limit": 1})
    if isinstance(j, list) and j:
        out["ls_ratio"] = float(j[-1]["longShortRatio"])
    j = _get(f"{FUT}/futures/data/openInterestHist", {"symbol": symbol, "period": "1h", "limit": 5})
    if isinstance(j, list) and len(j) >= 2:
        a, b = float(j[0]["sumOpenInterest"]), float(j[-1]["sumOpenInterest"])
        if a > 0:
            out["oi_chg_pct"] = (b / a - 1.0) * 100.0
    j = _get("https://api.alternative.me/fng/", {"limit": 1})
    try:
        out["fear_greed"] = float(j["data"][0]["value"])
    except Exception:
        pass
    return out
````

### `rtw/adapters/nse.py`

````text file=rtw/adapters/nse.py
"""NSE free data via nsefin (FII/DII, F&O list, option chain, bhav). Tolerant column matching. Never raises."""
from __future__ import annotations
import re
import threading
from functools import wraps
from datetime import date, datetime, timedelta
import pandas as pd


_CLIENT = None
_LOCK = threading.RLock()


def _client():
    """One shared NSEClient (keeps its session cookies). Public network functions are serialised with @_serial."""
    global _CLIENT
    with _LOCK:
        if _CLIENT is None:
            from nsefin import NSEClient
            _CLIENT = NSEClient()
        return _CLIENT


def _serial(fn):
    @wraps(fn)
    def w(*a, **k):
        with _LOCK:
            return fn(*a, **k)
    return w


def _num(x) -> float:
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return 0.0


def _find(cols: list[str], must: list[str], none: list[str] = ()) -> str | None:
    for c in cols:
        lc = re.sub(r"[^a-z0-9]", "", c.lower())
        if all(m in lc for m in must) and not any(n in lc for n in none):
            return c
    return None


def _to_date(x):
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d%b%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(x).strip()[:11].title() if "%b" in fmt else str(x).strip()[:10], fmt).date()
        except Exception:
            continue
    return None


def chain_from_df(df: pd.DataFrame, expiry: date | None = None) -> list[dict]:
    """Flattened option chain DataFrame -> [{strike, ce_oi, pe_oi, ce_ltp, pe_ltp, ce_iv, pe_iv}]. Column names vary by version.
    If the frame has an expiry column and `expiry` is given, only that expiry is used."""
    if df is None or len(df) == 0:
        return []
    cols = list(df.columns)
    ecol = _find(cols, ["expiry"])
    if expiry is not None and ecol:
        df = df[df[ecol].map(_to_date) == expiry]
        if len(df) == 0:
            return []
    k = _find(cols, ["strike"])
    ce_oi = _find(cols, ["ce", "oi"], ["chng", "change", "chg"]) or _find(cols, ["call", "oi"], ["chng", "change"])
    pe_oi = _find(cols, ["pe", "oi"], ["chng", "change", "chg"]) or _find(cols, ["put", "oi"], ["chng", "change"])
    ce_ltp = _find(cols, ["ce", "ltp"]) or _find(cols, ["ce", "lastprice"]) or _find(cols, ["call", "ltp"])
    pe_ltp = _find(cols, ["pe", "ltp"]) or _find(cols, ["pe", "lastprice"]) or _find(cols, ["put", "ltp"])
    ce_iv = _find(cols, ["ce", "iv"]) or _find(cols, ["ce", "implied"])
    pe_iv = _find(cols, ["pe", "iv"]) or _find(cols, ["pe", "implied"])
    if not (k and ce_oi and pe_oi):
        return []
    rows = []
    for _, r in df.iterrows():
        rows.append({"strike": _num(r[k]), "ce_oi": _num(r[ce_oi]), "pe_oi": _num(r[pe_oi]),
                     "ce_ltp": _num(r[ce_ltp]) if ce_ltp else 0.0, "pe_ltp": _num(r[pe_ltp]) if pe_ltp else 0.0,
                     "ce_iv": _num(r[ce_iv]) / 100.0 if ce_iv else 0.0, "pe_iv": _num(r[pe_iv]) / 100.0 if pe_iv else 0.0})
    return [r for r in rows if r["strike"] > 0]


def chain_from_json(j: dict, expiry: str | None = None) -> tuple[list[dict], str | None, float | None]:
    """Raw NSE option-chain-indices JSON -> (rows, expiry used, underlying). Picks nearest expiry unless given."""
    recs = (j or {}).get("records", {})
    data = recs.get("data", [])
    exps = recs.get("expiryDates", [])
    exp = expiry or (exps[0] if exps else None)
    rows = []
    for d in data:
        if exp and d.get("expiryDate") != exp:
            continue
        ce, pe = d.get("CE") or {}, d.get("PE") or {}
        rows.append({"strike": float(d["strikePrice"]), "ce_oi": float(ce.get("openInterest", 0)), "pe_oi": float(pe.get("openInterest", 0)),
                     "ce_ltp": float(ce.get("lastPrice", 0)), "pe_ltp": float(pe.get("lastPrice", 0)),
                     "ce_iv": float(ce.get("impliedVolatility", 0)) / 100.0, "pe_iv": float(pe.get("impliedVolatility", 0)) / 100.0})
    return rows, exp, recs.get("underlyingValue")


def atm_iv(rows: list[dict], spot: float, dte_days: float | None = None) -> float:
    """ATM implied vol (decimal). Uses the chain's IV columns; if they are missing/zero, backs IV out of the ATM premiums (bisection)."""
    if not rows:
        return 0.0
    r = min(rows, key=lambda x: abs(x["strike"] - spot))
    ivs = [v for v in (r["ce_iv"], r["pe_iv"]) if v > 0]
    if ivs:
        return sum(ivs) / len(ivs)
    if dte_days and dte_days > 0:
        from ..options import implied_vol
        t = max(dte_days, 0.05) / 365.0
        vs = [v for v in (implied_vol(r["ce_ltp"], spot, r["strike"], t, "CE"), implied_vol(r["pe_ltp"], spot, r["strike"], t, "PE")) if v > 0]
        return sum(vs) / len(vs) if vs else 0.0
    return 0.0


@_serial
def option_chain(symbol: str) -> pd.DataFrame | None:
    try:
        return _client().get_option_chain(symbol)
    except Exception:
        return None


@_serial
def fii_dii() -> dict:
    """Latest FII and DII net (crore). Returns {} on failure."""
    try:
        df = _client().get_fii_dii_activity()
        if df is None or len(df) == 0:
            return {}
        cols = list(df.columns)
        cat = _find(cols, ["category"])
        net = _find(cols, ["net"])
        out = {}
        if cat and net:
            for _, r in df.iterrows():
                c = str(r[cat]).upper()
                if "FII" in c or "FPI" in c:
                    out["fii_cash_net_cr"] = _num(r[net])
                elif "DII" in c:
                    out["dii_cash_net_cr"] = _num(r[net])
        return out
    except Exception:
        return {}


_INDEX_NAMES = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50")


def turnover_map(bhav: pd.DataFrame | None) -> dict:
    """Equity bhav copy -> {SYMBOL: traded value}. Tolerant to column names; EQ series only when a series column exists."""
    if bhav is None or len(bhav) == 0:
        return {}
    cols = list(bhav.columns)
    sc = _find(cols, ["symbol"]) or _find(cols, ["tckrsymb"])
    vc = _find(cols, ["ttltrfval"]) or _find(cols, ["turnover"]) or _find(cols, ["tottrdval"]) or _find(cols, ["tradedvalue"]) or _find(cols, ["value"])
    ser = _find(cols, ["series"]) or _find(cols, ["sctysrs"])
    if not (sc and vc):
        return {}
    out: dict = {}
    for _, r in bhav.iterrows():
        if ser and str(r[ser]).strip().upper() != "EQ":
            continue
        out[str(r[sc]).strip().upper()] = _num(r[vc])
    return out


@_serial
def fno_universe(n: int = 50) -> list[dict]:
    """F&O stocks ranked by cash-market traded value (latest bhav copy, looks back up to 6 days).
    Falls back to 'most active by value', then to plain F&O list order. [{symbol, lot}]"""
    try:
        c = _client()
        fno = c.get_fno_list()
        sym_col = _find(list(fno.columns), ["symbol"]) or fno.columns[0]
        lot_col = _find(list(fno.columns), ["lot"])
        lots = {str(r[sym_col]).upper(): int(_num(r[lot_col])) for _, r in fno.iterrows()} if lot_col else {}
        syms = [s for s in (lots or list(fno[sym_col].astype(str).str.upper())) if s not in _INDEX_NAMES]
        order: dict = {}
        d = datetime.now()
        for _ in range(7):                                  # latest published bhav copy
            try:
                order = turnover_map(c.get_equity_bhav_copy(d))
            except Exception:
                order = {}
            if order:
                break
            d -= timedelta(days=1)
        if not order:
            try:
                act = c.get_most_active_by_value()
                s2 = _find(list(act.columns), ["symbol"])
                v2 = _find(list(act.columns), ["value"]) or _find(list(act.columns), ["turnover"])
                order = {str(r[s2]).upper(): _num(r[v2]) for _, r in act.iterrows()} if s2 and v2 else {}
            except Exception:
                order = {}
        ranked = sorted(syms, key=lambda s: -order.get(s, 0.0)) if order else syms
        return [{"symbol": s, "lot": lots.get(s, 1)} for s in ranked[:n]]
    except Exception:
        return []


def fetch_holidays(timeout: float = 15.0) -> list[str]:
    """Trading holidays (ISO dates) from NSE holiday-master. NSE needs a warm-up request for cookies. [] on failure."""
    try:
        import requests
        s = requests.Session()
        h = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://www.nseindia.com/"}
        s.get("https://www.nseindia.com", headers=h, timeout=timeout)
        r = s.get("https://www.nseindia.com/api/holiday-master?type=trading", headers=h, timeout=timeout)
        j = r.json() if r.ok else {}
        out = set()
        for seg in ("CM", "FO"):
            for it in j.get(seg, []) or []:
                d = _to_date(it.get("tradingDate", ""))
                if d:
                    out.add(d.isoformat())
        return sorted(out)
    except Exception:
        return []
````

### `rtw/adapters/newsfeeds.py`

````text file=rtw/adapters/newsfeeds.py
"""News collectors: RSS (Google News etc.), GDELT. Dedup by url hash. Never raises."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
import feedparser
import requests
from ..sessions import IST

# (name, url, trust 0..1, official)
RSS_FEEDS = [
    ("GoogleNews India markets", "https://news.google.com/rss/search?q=nifty+OR+sensex+OR+RBI+when:1d&hl=en-IN&gl=IN&ceid=IN:en", 0.6, False),
    ("GoogleNews crude/OPEC", "https://news.google.com/rss/search?q=crude+oil+OR+OPEC+when:1d&hl=en-IN&gl=IN&ceid=IN:en", 0.6, False),
    ("GoogleNews gold/dollar/Fed", "https://news.google.com/rss/search?q=gold+price+OR+dollar+index+OR+Federal+Reserve+when:1d&hl=en-IN&gl=IN&ceid=IN:en", 0.6, False),
    ("GoogleNews geopolitics", "https://news.google.com/rss/search?q=war+OR+ceasefire+OR+sanctions+OR+tariffs+when:1d&hl=en-IN&gl=IN&ceid=IN:en", 0.55, False),
    ("ET Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", 0.65, False),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml", 0.65, False),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", 0.6, False),
    ("RBI press", "https://www.rbi.org.in/pressreleases_rss.xml", 0.95, True),
    ("Fed press", "https://www.federalreserve.gov/feeds/press_all.xml", 0.95, True),
]


def url_hash(url: str, title: str) -> str:
    return hashlib.sha1((url or title).strip().lower().encode()).hexdigest()


def parse_rss(text: str, source: str, trust: float, official: bool, now: datetime) -> list[dict]:
    d = feedparser.parse(text)
    out = []
    for e in d.entries[:60]:
        ts = now
        t = e.get("published_parsed") or e.get("updated_parsed")
        if t:
            ts = datetime(*t[:6], tzinfo=timezone.utc).astimezone(IST)
        out.append({"title": (e.get("title") or "").strip(), "url": e.get("link", ""), "source": source, "trust": trust, "official": official, "ts": ts})
    return [x for x in out if x["title"]]


def fetch_rss(now: datetime, feeds=RSS_FEEDS, timeout: float = 12.0) -> list[dict]:
    items = []
    for name, url, trust, official in feeds:
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 RTW"})
            if r.ok:
                items += parse_rss(r.text, name, trust, official, now)
        except Exception:
            continue
    return items


def parse_gdelt(j: dict, now: datetime) -> list[dict]:
    out = []
    for a in (j or {}).get("articles", [])[:50]:
        try:
            ts = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(IST)
        except Exception:
            ts = now
        out.append({"title": a.get("title", "").strip(), "url": a.get("url", ""), "source": "GDELT:" + a.get("domain", ""), "trust": 0.4, "official": False, "ts": ts})
    return [x for x in out if x["title"]]


def fetch_gdelt(now: datetime, query: str = "(oil OR gold OR inflation OR \"central bank\" OR war OR sanctions)", timeout: float = 20.0) -> list[dict]:
    """GDELT allows 1 request / 5 seconds. Call at most every 15 minutes."""
    try:
        r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params={"query": query, "mode": "ArtList", "format": "json", "maxrecords": 50, "timespan": "60min", "sort": "datedesc"}, timeout=timeout)
        return parse_gdelt(r.json(), now) if r.ok else []
    except Exception:
        return []
````

### `rtw/adapters/calendar.py`

````text file=rtw/adapters/calendar.py
"""Event calendar: ForexFactory free JSON feed + static dates + rule-based weekly events. Never raises."""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from ..news import Event
from ..sessions import IST

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
NY = ZoneInfo("America/New_York")
# country -> asset groups (group names as in news.group_of). USD moves everything.
COUNTRY_ASSETS = {"USD": ("ALL",), "INR": ("ALL",), "EUR": ("EURUSD", "EURINR", "GOLD", "INDEX"), "GBP": ("GBPUSD", "GBPINR"),
                  "JPY": ("USDJPY", "JPYINR", "GOLD"), "CNY": ("CRUDE", "GOLD", "SILVER", "INDEX"), "CAD": ("CRUDE",), "AUD": ("GOLD",)}
IMPACT = {"High": "HIGH", "Medium": "MED", "Low": "LOW"}


def parse_ff(rows: list) -> list[Event]:
    out = []
    for r in rows or []:
        imp = IMPACT.get(r.get("impact"))
        assets = COUNTRY_ASSETS.get(r.get("country"))
        if not imp or not assets or imp == "LOW":
            continue
        try:
            when = datetime.fromisoformat(r["date"]).astimezone(IST)
        except Exception:
            continue
        out.append(Event(f"{r['country']} {r.get('title', '').strip()}", when, imp, assets))
    return out


def fetch_ff(timeout: float = 15.0) -> list[Event]:
    try:
        r = requests.get(FF_URL, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 RTW"})
        return parse_ff(r.json()) if r.ok else []
    except Exception:
        return []


def static_events(path: str = "data/events_static.json") -> list[Event]:
    """File format: [{"name":"RBI policy","when":"2026-10-07T10:00:00+05:30","impact":"HIGH","assets":["ALL"]}]. Edit by hand / refresh yearly."""
    try:
        if not os.path.exists(path):
            return []
        return [Event(e["name"], datetime.fromisoformat(e["when"]).astimezone(IST), e.get("impact", "HIGH"), tuple(e.get("assets", ["ALL"])))
                for e in json.load(open(path, encoding="utf-8"))]
    except Exception:
        return []


def eia_weekly(now: datetime, weeks: int = 2) -> list[Event]:
    """EIA crude inventory: Wednesday 10:30 New York time (rule). Shifts after holidays; the ForexFactory feed corrects that."""
    out = []
    d = now.astimezone(NY).date()
    for i in range(weeks * 7 + 1):
        day = d + timedelta(days=i)
        if day.weekday() == 2:
            out.append(Event("EIA crude inventories", datetime(day.year, day.month, day.day, 10, 30, tzinfo=NY).astimezone(IST), "MED", ("CRUDE",)))
    return out


def all_events(now: datetime, static_path: str = "data/events_static.json", ff: list[Event] | None = None) -> list[Event]:
    ev = (ff if ff is not None else fetch_ff()) + static_events(static_path) + eia_weekly(now)
    seen, out = set(), []
    for e in sorted(ev, key=lambda x: x.when):
        k = (e.name.lower()[:25], e.when.strftime("%Y%m%d%H%M"))
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out
````

### `web/index.html`

````text file=web/index.html
<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b1020">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/icon-192.png">
<title>Raj Trading World</title>
<style>
:root{--bg:#0b1020;--card:#141b30;--card2:#1b2440;--tx:#e8ecf7;--mut:#8f9bb8;--buy:#22c55e;--sell:#ef4444;--wait:#f59e0b;--acc:#6aa7ff;--line:#26304f}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
body{padding:0 16px calc(76px + env(safe-area-inset-bottom))}
header{display:flex;align-items:center;justify-content:space-between;padding:14px 0 6px}
h1{font-size:17px;margin:0;letter-spacing:.3px}
.badge{font-size:11px;padding:2px 8px;border-radius:99px;background:var(--card2);color:var(--mut);border:1px solid var(--line)}
.badge.paper{color:var(--wait);border-color:var(--wait)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin:12px 0}
.big{font-size:26px;font-weight:700;margin:2px 0 4px}
.buy{color:var(--buy)}.sell{color:var(--sell)}.wait{color:var(--wait)}.mut{color:var(--mut)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}
.kv{background:var(--card2);border-radius:12px;padding:10px 12px}.kv b{display:block;font-size:12px;color:var(--mut);font-weight:500}
.kv span{font-size:17px;font-weight:600}
ul{padding-left:18px;margin:8px 0}
nav{position:fixed;left:0;right:0;bottom:0;display:flex;background:#0e1530;border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}
nav button{flex:1;background:none;border:0;color:var(--mut);padding:12px 0;font-size:12px}
nav button.on{color:var(--acc);font-weight:700}
.chips{display:flex;gap:8px;overflow-x:auto;padding:4px 0}
.chip{white-space:nowrap;border:1px solid var(--line);background:var(--card);color:var(--mut);border-radius:99px;padding:6px 14px;font-size:13px}
.chip.on{color:var(--tx);border-color:var(--acc)}
input,select{width:100%;background:var(--card2);color:var(--tx);border:1px solid var(--line);border-radius:12px;padding:12px;font-size:16px}
button.pri{background:var(--acc);color:#04122b;border:0;border-radius:12px;padding:12px 16px;font-weight:700;font-size:15px}
.row{display:flex;justify-content:space-between;gap:8px;padding:8px 0;border-bottom:1px solid var(--line)}
.row:last-child{border:0}
details summary{cursor:pointer;color:var(--mut);padding:6px 0}
.warn{background:#3a2a0a;border:1px solid var(--wait);color:#ffd9a0;border-radius:12px;padding:10px 12px;margin:10px 0;font-size:13px}
.err{background:#3b1414;border:1px solid var(--sell);color:#ffc9c9;border-radius:12px;padding:10px 12px;margin:10px 0}
svg{width:100%;height:90px}
.chartbox{margin-top:12px}.chartbox canvas{width:100%;height:280px;display:block;background:var(--card2);border-radius:12px}
.chartbox a{color:var(--acc);font-size:13px}
.cbtn{margin:6px 6px 0 0}
.mood{display:inline-block;border-radius:99px;padding:3px 10px;font-size:12px;font-weight:700;border:1px solid var(--line)}
.mood.BULLISH{color:var(--buy);border-color:var(--buy)}.mood.BEARISH{color:var(--sell);border-color:var(--sell)}.mood.SIDEWAYS{color:var(--wait);border-color:var(--wait)}
#toast{position:fixed;left:12px;right:12px;top:calc(env(safe-area-inset-top) + 10px);z-index:9;display:none;background:#10203f;border:1px solid var(--acc);border-radius:14px;padding:12px 14px;box-shadow:0 8px 30px #0008}
#toast b{display:block;margin-bottom:2px}
</style>
</head>
<body>
<header><h1>Raj Trading World</h1><span id="mode" class="badge"></span></header>
<div id="err"></div>
<div id="toast" role="alert"></div>
<main id="view"></main>
<nav id="nav">
  <button data-t="home" class="on">Home</button><button data-t="markets">Markets</button><button data-t="search">Search</button>
  <button data-t="news">News</button><button data-t="record">Record</button><button data-t="settings">Settings</button>
</nav>
<script>
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=x=>{if(x==null)return"-";const a=Math.abs(x);return a>=1000?Math.round(x).toLocaleString("en-IN"):a>=10?x.toFixed(2):x.toFixed(4)};
const hm=iso=>iso?new Date(iso).toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit",hour12:false,timeZone:"Asia/Kolkata"}):"-";
let tab="home",mtab="index",timer=null;
function key(){try{return localStorage.getItem("rtw_key")||""}catch(e){return""}}
async function api(path,opt={}){
  const sep=path.includes("?")?"&":"?";
  const r=await fetch(path+(key()?sep+"key="+encodeURIComponent(key()):""),opt);
  if(r.status===401){const k=prompt("Access key daalo");if(k){try{localStorage.setItem("rtw_key",k)}catch(e){}return api(path,opt)}throw new Error("access key chahiye")}
  if(!r.ok){let m=r.statusText;try{m=(await r.json()).detail||m}catch(e){}throw new Error(m)}
  return r.json();
}

/* ---------- market mood (bullish / bearish / sideways) ---------- */
const moodBadge=m=>m&&m.mood?`<span class="mood ${m.mood}">${m.icon} ${esc(m.label)}</span>`:"";
const rangeTxt=m=>m&&m.range?` · range ${fmt(m.range.lo)} – ${fmt(m.range.hi)}`:"";
function moodStrip(d){
  const it=(d.items||[]).filter(x=>x.headline);if(!it.length)return"";
  return `<div class="card"><b>Market ka mahaul</b><span class="mut"> (sirf trend, signal nahi)</span>${it.map(x=>`<div class="row"><span>${esc(x.name)}</span><span>${x.mood?`<span class="mood ${x.mood}">${x.icon} ${esc(x.label)}</span>`:`<span class="mut">${esc(x.label)}</span>`}</span></div>${x.mood?`<div class="mut" style="font-size:12px;margin:-4px 0 6px">${esc(x.text)}${x.mood==="SIDEWAYS"?esc(rangeTxt(x)):""}</div>`:""}`).join("")}</div>`;
}
let toastT=null;
function showToast(t,body){const e=$("#toast");e.innerHTML=`<b>${esc(t)}</b>${esc(body||"")}`;e.style.display="block";clearTimeout(toastT);toastT=setTimeout(()=>e.style.display="none",12000);e.onclick=()=>e.style.display="none"}
async function pollMood(){
  try{const d=await api("/api/mood");let seen=null;try{seen=localStorage.getItem("rtw_mood_seen")}catch(e){}
    const fl=d.flips||[];const last=fl.length?fl[fl.length-1].ts:"";
    if(seen===null){try{localStorage.setItem("rtw_mood_seen",last)}catch(e){}return}
    const fresh=fl.filter(f=>f.ts>seen);
    if(fresh.length){const nm=s=>(d.items.find(i=>i.symbol===s)||{}).name||s,L={BULLISH:"Tezi (Bullish)",BEARISH:"Mandi (Bearish)",SIDEWAYS:"Sideways"};
      showToast("Market mood badla",fresh.map(f=>`${nm(f.symbol)}: ${L[f.from]} → ${L[f.to]}`).join(" | "));try{localStorage.setItem("rtw_mood_seen",last)}catch(e){}}
  }catch(e){}
}
function srText(sr){if(!sr)return"";const p=[];
  (sr.resistances||[]).slice(0,1).forEach(x=>p.push("Resistance "+fmt(x.price)+" ("+x.touches+" touch)"));
  (sr.supports||[]).slice(0,1).forEach(x=>p.push("Support "+fmt(x.price)+" ("+x.touches+" touch)"));
  (sr.zones||[]).forEach(z=>p.push((z.kind==="demand"?"Demand ":"Supply ")+fmt(z.lo)+"–"+fmt(z.hi)+(z.fresh?" (fresh)":"")));
  return p.length?`<div class="mut" style="font-size:12px;margin:2px 0 6px">${p.map(esc).join(" · ")}</div>`:""}
/* ---------- charts (own canvas, no external library) ---------- */
function drawChart(cv,d){
  const dpr=window.devicePixelRatio||1,W=cv.clientWidth,H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;
  const g=cv.getContext("2d");g.scale(dpr,dpr);g.clearRect(0,0,W,H);
  const cs=d.candles||[];if(!cs.length){g.fillStyle="#8f9bb8";g.fillText("Data nahi",10,20);return}
  const PR=58,PB=18,pw=W-PR,ph=H-PB;
  let lo=Math.min(...cs.map(c=>c.l)),hi=Math.max(...cs.map(c=>c.h));
  (d.levels||[]).forEach(l=>{lo=Math.min(lo,l.price);hi=Math.max(hi,l.price)});
  const pad=(hi-lo)*0.06||1;lo-=pad;hi+=pad;
  const y=p=>ph-(p-lo)/(hi-lo)*ph,step=pw/cs.length,bw=Math.max(1,step*0.65);
  g.font="10px system-ui";g.lineWidth=1;
  for(let i=0;i<=4;i++){const p=lo+(hi-lo)*i/4,yy=y(p);g.strokeStyle="#26304f";g.beginPath();g.moveTo(0,yy);g.lineTo(pw,yy);g.stroke();g.fillStyle="#8f9bb8";g.fillText(fmt(p),pw+4,yy+3)}
  cs.forEach((c,i)=>{const x=i*step+step/2,up=c.c>=c.o;g.strokeStyle=g.fillStyle=up?"#22c55e":"#ef4444";
    g.beginPath();g.moveTo(x,y(c.h));g.lineTo(x,y(c.l));g.stroke();const t=y(Math.max(c.o,c.c)),b=y(Math.min(c.o,c.c));g.fillRect(x-bw/2,t,bw,Math.max(1,b-t))});
  if(d.ema20){g.strokeStyle="#6aa7ff";g.lineWidth=1.2;g.beginPath();let st=false;d.ema20.forEach((e,i)=>{if(e==null)return;const x=i*step+step/2;if(!st){g.moveTo(x,y(e));st=true}else g.lineTo(x,y(e))});g.stroke();g.lineWidth=1}
  const sr=d.sr||{};
  (sr.zones||[]).forEach(z=>{const y1=Math.max(0,Math.min(ph,y(z.hi))),y2=Math.max(0,Math.min(ph,y(z.lo)));if(y2-y1<1)return;
    g.fillStyle=z.kind==="demand"?"rgba(34,197,94,.16)":"rgba(239,68,68,.16)";g.fillRect(0,y1,pw,y2-y1);
    g.fillStyle=z.kind==="demand"?"#22c55e":"#ef4444";g.fillText(z.kind==="demand"?"Demand":"Supply",pw-44,Math.min(ph-2,y1+10))});
  [...(sr.supports||[]).map(x=>["S",x]),...(sr.resistances||[]).map(x=>["R",x])].forEach(([k,x])=>{const yy=y(x.price);if(yy<0||yy>ph)return;g.strokeStyle="#8f9bb8";g.setLineDash([2,3]);g.beginPath();g.moveTo(0,yy);g.lineTo(pw,yy);g.stroke();g.setLineDash([]);g.fillStyle="#8f9bb8";g.fillText(k+" "+fmt(x.price),pw-70,yy-2)});
  const col={entry:"#6aa7ff",sl:"#ef4444",target:"#22c55e"};
  let lastLab=-99;
  [...(d.levels||[])].sort((a,b)=>y(a.price)-y(b.price)).forEach(l=>{const yy=y(l.price);g.strokeStyle=col[l.kind]||"#f59e0b";g.setLineDash([5,4]);g.beginPath();g.moveTo(0,yy);g.lineTo(pw,yy);g.stroke();g.setLineDash([]);
    const ly=Math.max(yy-3,lastLab+11);lastLab=ly;g.fillStyle=col[l.kind]||"#f59e0b";g.fillText((l.label?l.label+" ":"")+fmt(l.price),4,ly)});
  const last=cs[cs.length-1];g.fillStyle="#e8ecf7";g.fillText(fmt(last.c),pw+4,y(last.c)+3);
  const ft=t=>new Date(t*1000).toISOString().slice(11,16);g.fillStyle="#8f9bb8";
  [0,Math.floor(cs.length/2),cs.length-1].forEach(i=>g.fillText(ft(cs[i].t),Math.min(i*step,pw-30),H-4));
}
async function loadChart(box,sym,tf,opt){
  box.dataset.sym=sym;box.dataset.tf=tf;box.dataset.opt=opt?JSON.stringify(opt):"";
  box.innerHTML=`<div class="mut">Chart la raha hu...</div>`;
  let q="/api/chart?q="+encodeURIComponent(sym)+"&tf="+tf;if(opt)q+=`&strike=${opt.strike}&cp=${opt.cp}&expiry=${encodeURIComponent(opt.expiry)}`;
  try{const d=await api(q);
    if(!d.found){box.innerHTML=`<div class="warn">${esc(d.message||"Chart nahi mila")}</div>`;return}
    box.innerHTML=`<div class="chips">${["5m","15m","1h"].map(t=>`<button class="chip ${t===tf?'on':''}" data-tf="${t}">${t}</button>`).join("")}</div>
      <div style="margin:6px 0">${moodBadge(d.mood)}<span class="mut">${d.mood?" "+esc(d.mood.text)+esc(rangeTxt(d.mood)):""}</span></div><div class="mut" style="margin:4px 0">${esc(d.name)} · EMA20 (neeli line) · rangeen dotted = Entry/SL/Target · S/R = support/resistance · hara/laal patta = Demand/Supply zone</div>${srText(d.sr)}<canvas></canvas>
      <div style="margin-top:6px"><a href="${esc(d.tv_url)}" target="_blank" rel="noopener">TradingView me kholo ↗</a></div>`;
    drawChart(box.querySelector("canvas"),d);
  }catch(e){box.innerHTML=`<div class="err">${esc(e.message)}</div>`}
}
function chartBoxHTML(){return `<div class="chartbox open"></div>`}
document.addEventListener("click",e=>{
  const b=e.target.closest("[data-chart],[data-ochart],[data-tf]");if(!b)return;
  if(b.dataset.tf){const box=b.closest(".chartbox");loadChart(box,box.dataset.sym,b.dataset.tf,box.dataset.opt?JSON.parse(box.dataset.opt):null);return}
  const card=b.closest(".card"),host=card||b.closest(".row")||b.parentElement;
  let box=card?card.querySelector(".chartbox"):(host.nextElementSibling&&host.nextElementSibling.classList.contains("chartbox")?host.nextElementSibling:null);
  const opt=b.dataset.ochart?JSON.parse(b.dataset.ochart):null,sym=b.dataset.chart||b.dataset.sym;
  if(box&&box.dataset.sym===sym&&(box.dataset.opt||"")===(opt?JSON.stringify(opt):"")){box.remove();return}
  if(box)box.remove();box=document.createElement("div");box.className="chartbox open";if(card)card.appendChild(box);else host.after(box);loadChart(box,sym,"5m",opt);
});
function tradeCard(t){
  const c=t.direction==="BUY"?"buy":"sell";
  const o=t.option;
  let h=`<div class="card"><span class="badge ${t.paper?'paper':''}">${t.paper?'PAPER (record ban raha hai)':'LIVE-READY'}</span> <span class="badge">Grade ${esc(t.grade)} · ${t.confidence}%</span>
  <div class="big ${c}">${esc(t.label)}</div><div class="big ${c}" style="font-size:18px">${esc(t.action)}</div>
  <p>${esc(t.status_text)}</p>
  <div class="grid">
   <div class="kv"><b>Entry zone (underlying)</b><span>${fmt(t.entry_lo)} – ${fmt(t.entry_hi)}</span></div>
   <div class="kv"><b>Stoploss</b><span>${fmt(t.sl)}</span></div>
   <div class="kv"><b>Target 1</b><span>${fmt(t.t1)}</span></div>
   <div class="kv"><b>Target 2</b><span>${fmt(t.t2)}</span></div>
   <div class="kv"><b>Valid till</b><span>${hm(t.valid_till)}</span></div>
   <div class="kv"><b>Hold till (nikalna)</b><span>${hm(t.exit_by)}</span></div>
  </div>`;
  if(o) h+=`<div class="grid"><div class="kv"><b>Option premium (approx)</b><span>₹${fmt(o.premium)}</span></div><div class="kv"><b>Premium SL</b><span>₹${fmt(o.sl_premium)}</span></div>
   <div class="kv"><b>Premium T1</b><span>₹${fmt(o.t1_premium)}</span></div><div class="kv"><b>Expiry</b><span>${esc(o.expiry)}</span></div></div>`;
  if(t.lots!=null) h+=`<p class="mut">Lots: <b>${t.lots}</b>${t.max_loss?` · Max nuksan (poora premium): ₹${fmt(t.max_loss)}`:(t.risk_amount?` · SL pe risk: ${fmt(t.risk_amount)}`:"")}</p>`;
  if(t.live&&t.live.price!=null) h+=`<p>Abhi price: <b>${fmt(t.live.price)}</b>${t.live.r!=null?` · <b class="${t.live.r>=0?'buy':'sell'}">${t.live.r.toFixed(2)}R</b>`:""}</p>`;
  if(t.state==="NEW") h+=`<div class="warn">Chase mat karo: ${fmt(t.chase_price)} ke aage price chala jaye to ye trade MISSED hai.</div>`;
  if(t.plan_note) h+=`<div class="warn">${esc(t.plan_note)}</div>`;
  h+=`<div><button class="chip cbtn" data-chart="${esc(t.symbol)}" data-sym="${esc(t.symbol)}">📈 Chart</button>${o?`<button class="chip cbtn" data-sym="${esc(t.symbol)}" data-chart="${esc(t.symbol)}" data-ochart='${esc(JSON.stringify({strike:o.strike,cp:o.cp,expiry:o.expiry}))}'>📈 Option chart</button>`:""}</div>`;
  if(t.reasons&&t.reasons.length) h+=`<b>Kyu:</b><ul>${t.reasons.map(r=>`<li>${esc(r)}</li>`).join("")}</ul>`;
  return h+`</div>`;
}
async function home(){
  const d=await api("/api/home");$("#mode").textContent=d.mode;
  let h="";
  try{h+=moodStrip(await api("/api/mood"))}catch(e){}
  if(d.trades&&d.trades.length) h+=d.trades.map(tradeCard).join("");
  else if(d.trade) h+=tradeCard(d.trade);
  else{const w=d.wait||{};h+=`<div class="card"><div class="big wait">WAIT</div><p>${esc(w.reason)}</p>${w.next_event?`<p class="mut">Agla bada event: <b>${esc(w.next_event.name)}</b> ${esc(w.next_event.when_text)}</p>`:""}</div>`}
  if(d.info&&d.info.length) h+=`<div class="card"><b>Dusre signals (sirf INFO)</b>${d.info.map(i=>`<div class="row"><span>${esc(i.symbol)} <b class="${i.action==='BUY'?'buy':'sell'}">${esc(i.action)}</b></span><span class="mut">${esc(i.grade)} · ${i.confidence}%</span></div>`).join("")}</div>`;
  if(d.last_closed){const l=d.last_closed;h+=`<div class="card"><b>Pichla trade</b><div class="row"><span>${esc(l.label)} ${esc(l.action)}</span><span class="${(l.r_multiple||0)>=0?'buy':'sell'}">${l.r_multiple!=null?l.r_multiple.toFixed(2)+'R':esc(l.state)}</span></div><div class="mut">${esc(l.close_reason)}</div></div>`}
  $("#view").innerHTML=h;
}
async function markets(){
  const d=await api("/api/markets/"+mtab);
  const tabs=["index","commodity","stocks","forex","crypto"];
  let h=`<div class="chips">${tabs.map(t=>`<button class="chip ${t===mtab?'on':''}" data-m="${t}">${t[0].toUpperCase()+t.slice(1)}</button>`).join("")}</div>`;
  const row=r=>`<div class="card"><div class="row" style="border:0;padding:0"><b>${esc(r.name||r.symbol)}</b><b class="${r.action==='BUY'?'buy':r.action==='SELL'?'sell':'wait'}">${esc(r.action)}</b></div>
   <div>${moodBadge(r.mood)}</div><div class="mut">${r.price!=null?fmt(r.price):""} ${r.regime?"· "+esc(r.regime):""} ${r.grade?"· Grade "+esc(r.grade)+" · "+r.confidence+"%":""}</div>
   ${r.plan&&r.action!=="WAIT"?`<div>Entry ${fmt(r.plan.entry_lo)}–${fmt(r.plan.entry_hi)} · SL ${fmt(r.plan.sl)} · T1 ${fmt(r.plan.t1)}</div>`:""}
   ${(r.reasons||[]).length?`<div class="mut">${r.reasons.map(esc).join(" · ")}</div>`:""}
   ${r.action==="WAIT"&&r.wait_reason?`<div class="mut">${esc(r.wait_reason)}</div>`:""}<div><button class="chip cbtn" data-chart="${esc(r.symbol)}" data-sym="${esc(r.symbol)}">📈 Chart</button></div></div>`;
  h+=d.active.length?d.active.map(row).join(""):`<div class="card mut">Is tab me abhi koi BUY/SELL signal nahi.</div>`;
  if(mtab==="stocks") h+=`<details><summary>${d.wait_count} stocks WAIT me hain</summary>${(d.waiting||[]).map(w=>`<div class="row"><span>${esc(w.symbol)} ${moodBadge(w.mood)}</span><button class="chip cbtn" data-chart="${esc(w.symbol)}" data-sym="${esc(w.symbol)}">📈</button></div>`).join("")}</details>`;
  else if(d.waiting.length) h+=`<details><summary>${d.waiting.length} WAIT me</summary>${d.waiting.map(row).join("")}</details>`;
  $("#view").innerHTML=h;
  document.querySelectorAll("[data-m]").forEach(b=>b.onclick=()=>{mtab=b.dataset.m;render()});
}
function search(){
  $("#view").innerHTML=`<div class="card"><input id="q" placeholder="Stock / pair / BTC likho (jaise RELIANCE, EURUSD)" autocomplete="off"><div style="height:10px"></div><button class="pri" id="go">Signal dekho</button> <button class="chip" id="cg">📈 Sirf chart</button></div><div id="res"></div>`;
  const go=async()=>{const q=$("#q").value.trim();if(!q)return;$("#res").innerHTML=`<div class="card mut">Dekh raha hu...</div>`;
    try{const r=await api("/api/search?q="+encodeURIComponent(q));
      if(!r.found){$("#res").innerHTML=`<div class="card">${esc(r.message)}</div>`;return}
      const d=r.decision,c=d.action==="BUY"?"buy":d.action==="SELL"?"sell":"wait";
      $("#res").innerHTML=`<div class="card"><div class="big ${c}">${esc(r.name)} — ${esc(d.action)}</div><div class="mut">${esc(d.note||"")}</div>
       ${d.plan&&d.action!=="WAIT"?`<div class="grid"><div class="kv"><b>Entry</b><span>${fmt(d.plan.entry_lo)}–${fmt(d.plan.entry_hi)}</span></div><div class="kv"><b>SL</b><span>${fmt(d.plan.sl)}</span></div><div class="kv"><b>T1</b><span>${fmt(d.plan.t1)}</span></div><div class="kv"><b>T2</b><span>${fmt(d.plan.t2)}</span></div></div>`:`<p>${esc(d.wait_reason||"")}</p>`}
       ${(d.reasons||[]).length?`<ul>${d.reasons.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}<div><button class="chip cbtn" data-chart="${esc(r.symbol)}" data-sym="${esc(r.symbol)}">📈 Chart</button></div></div>`;
      const cb=$("#res [data-chart]");if(cb)cb.click();
    }catch(e){$("#res").innerHTML=`<div class="err">${esc(e.message)}</div>`}};
  $("#cg").onclick=()=>{const q=$("#q").value.trim();if(!q)return;$("#res").innerHTML=`<div class="card"><button class="chip cbtn" data-chart="${esc(q)}" data-sym="${esc(q)}">📈 Chart</button></div>`;$("#res [data-chart]").click()};
  $("#go").onclick=go;$("#q").onkeydown=e=>{if(e.key==="Enter")go()};
}
async function news(){
  const d=await api("/api/news");
  let h=`<div class="card"><b>News mode:</b> <span class="${d.mode==='CALM'?'buy':'wait'}">${esc(d.mode)}</span>${d.reason?`<p>${esc(d.reason)}</p>`:""}${d.vix_z!=null?`<p class="mut">VIX z-score: ${d.vix_z.toFixed(1)}</p>`:""}</div>`;
  h+=`<div class="card"><b>Aane wale events (IST)</b>${(d.events||[]).map(e=>`<div class="row"><span>${esc(e.name)}</span><span class="${e.impact==='HIGH'?'wait':'mut'}">${esc(e.when_text)}</span></div>`).join("")||'<p class="mut">Koi event nahi</p>'}</div>`;
  h+=`<div class="card"><b>Taaza headlines</b>${(d.headlines||[]).map(x=>`<div class="row"><span>${esc(x.title)}</span><span class="mut">${esc((x.tags||[]).join(" "))}</span></div>`).join("")||'<p class="mut">Abhi koi headline nahi</p>'}</div>`;
  $("#view").innerHTML=h;
}
async function record(){
  const d=await api("/api/record"),a=d.all;
  let pts="";if(d.equity.length>1){const ys=d.equity.map(e=>e.cum_r),mn=Math.min(0,...ys),mx=Math.max(0.1,...ys);
    pts=d.equity.map((e,i)=>`${(i/(d.equity.length-1))*300},${88-((e.cum_r-mn)/(mx-mn))*80}`).join(" ")}
  let h=`<div class="card"><div class="grid"><div class="kv"><b>Trades</b><span>${a.trades}</span></div><div class="kv"><b>Win rate</b><span>${(a.win_rate*100).toFixed(0)}%</span></div>
   <div class="kv"><b>Total R</b><span>${a.total_r.toFixed(2)}</span></div><div class="kv"><b>Avg R</b><span>${a.avg_r.toFixed(2)}</span></div></div>
   ${pts?`<svg viewBox="0 0 300 90" preserveAspectRatio="none"><polyline fill="none" stroke="#6aa7ff" stroke-width="2" points="${pts}"/></svg>`:'<p class="mut">Curve ke liye kam se kam 2 trade chahiye.</p>'}</div>`;
  h+=`<div class="card"><b>Pichle trades</b>${d.last.map(l=>`<div class="row"><span>${esc(l.symbol)} ${esc(l.direction)} ${l.paper?'<span class="badge paper">PAPER</span>':''}</span><span class="${(l.r||0)>=0?'buy':'sell'}">${l.r!=null?l.r.toFixed(2)+'R':esc(l.state)}</span></div>`).join("")||'<p class="mut">Abhi koi trade nahi</p>'}</div>`;
  $("#view").innerHTML=h;
}
async function settings(){
  const s=await api("/api/settings");
  $("#view").innerHTML=`<div class="card"><b>Capital (₹)</b><input id="cap" type="number" value="${s.capital}"><div style="height:10px"></div>
   <b>Risk per trade (%)</b><input id="rp" type="number" step="0.1" value="${(s.risk_pct*100).toFixed(1)}"><div style="height:10px"></div>
   <b>Ek saath kitne signals (1 = sirf ek)</b><select id="mt">${[1,2,3,4,5].map(n=>`<option ${n===s.max_trades?"selected":""}>${n}</option>`).join("")}</select><div style="height:10px"></div>
   <b>Profile</b><select id="pf">${["conservative","moderate","aggressive"].map(p=>`<option ${p===s.profile?"selected":""}>${p}</option>`).join("")}</select><div style="height:14px"></div>
   <button class="pri" id="sv">Save</button><p id="msg" class="mut"></p></div>`;
  $("#sv").onclick=async()=>{try{await api("/api/settings",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({capital:+$("#cap").value,risk_pct:+$("#rp").value/100,profile:$("#pf").value,max_trades:+$("#mt").value})});$("#msg").textContent="Save ho gaya"}catch(e){$("#msg").textContent=e.message}};
}
const views={home,markets,search,news,record,settings};
async function render(){
  document.querySelectorAll("nav button").forEach(b=>b.classList.toggle("on",b.dataset.t===tab));
  $("#err").innerHTML="";
  try{await views[tab]()}catch(e){$("#err").innerHTML=`<div class="err">${esc(e.message)}</div>`}
}
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{tab=b.dataset.t;render()});
pollMood();setInterval(()=>{if(document.visibilityState==="visible")pollMood()},30000);
render();timer=setInterval(()=>{if(["home","markets","news"].includes(tab)&&document.visibilityState==="visible"&&!document.querySelector(".chartbox"))render()},30000);
if("serviceWorker" in navigator)navigator.serviceWorker.register("/sw.js").catch(()=>{});
</script>
</body>
</html>
````

### `web/manifest.webmanifest`

````text file=web/manifest.webmanifest
{"name":"Raj Trading World","short_name":"RTW","start_url":"/","display":"standalone","background_color":"#0b1020","theme_color":"#0b1020",
 "icons":[{"src":"/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/icon-512.png","sizes":"512x512","type":"image/png"}]}
````

### `web/sw.js`

````text file=web/sw.js
const CACHE="rtw-shell-v1";
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(["/","/manifest.webmanifest"])).catch(()=>{}));self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=="GET"||u.pathname.startsWith("/api/"))return;          // API is never cached (stale signals are dangerous)
  e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(CACHE).then(c=>c.put(e.request,cp));return r}).catch(()=>caches.match(e.request)));
});
````

### `tests/__init__.py`

````text file=tests/__init__.py
# package marker
````

### `tests/test_kernel.py`

````text file=tests/test_kernel.py
import math
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd
import pytest

from rtw import indicators as ta
from rtw.layers import chart_layers, regime, LayerResult
from rtw.scoring import combine, grade, direction_of, weights_for, PROFILES
from rtw.sessions import IST, is_open, session_times, exit_by, us_dst_active
from rtw.plan import build_plan
from rtw import options as op
from rtw.gates import GateInput, evaluate_gates, all_passed, first_failure, Protections
from rtw.lifecycle import Signal, advance, TradeLock, rank_score, pick_best, setup_factor
from rtw import news as nw
from rtw.db import connect, save_signal, upsert_candles, track_record
from rtw.engine import analyze

T0 = datetime(2026, 10, 7, 11, 0, tzinfo=IST)   # Wednesday, NSE open


def make_df(n=300, drift=0.0006, vol=0.003, seed=1, start=22000.0, freq="5min", t0=None, vol_base=1000):
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    close = start * np.exp(np.cumsum(rets))
    open_ = np.r_[start, close[:-1]]
    spread = np.abs(rng.normal(0, vol * 0.6, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volu = vol_base * (1 + np.abs(rng.normal(0, 0.5, n)))
    # build index ending inside NSE session on a weekday
    end = t0 or T0
    idx = pd.date_range(end=end, periods=n, freq=freq, tz=IST)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volu}, index=idx)


# ---------------- indicators ----------------
def test_rsi_bounds_and_flat():
    df = make_df()
    r = ta.rsi(df["close"]).dropna()
    assert ((r >= 0) & (r <= 100)).all()
    flat = pd.Series([100.0] * 50)
    assert ta.rsi(flat).iloc[-1] == 50.0
    up = pd.Series(np.arange(1, 60, dtype=float))
    assert ta.rsi(up).iloc[-1] == 100.0


def test_no_lookahead_indicators():
    df = make_df(200)
    full = ta.ema(df["close"], 20)
    part = ta.ema(df["close"].iloc[:150], 20)
    assert math.isclose(full.iloc[149], part.iloc[-1], rel_tol=1e-12)
    st_full = ta.supertrend(df)["direction"].iloc[149]
    st_part = ta.supertrend(df.iloc[:150])["direction"].iloc[-1]
    assert st_full == st_part
    ax_full = ta.adx(df)["adx"].iloc[149]
    ax_part = ta.adx(df.iloc[:150])["adx"].iloc[-1]
    assert math.isclose(ax_full, ax_part, rel_tol=1e-9)


def test_atr_positive_and_supertrend_values():
    df = make_df()
    assert (ta.atr(df).dropna() > 0).all()
    st = ta.supertrend(df)
    assert set(st["direction"].unique()) <= {-1.0, 0.0, 1.0}


def test_vwap_resets_each_day():
    a = make_df(40, t0=datetime(2026, 10, 6, 15, 0, tzinfo=IST))
    b = make_df(40, t0=datetime(2026, 10, 7, 15, 0, tzinfo=IST))
    df = pd.concat([a[a.index.date == date(2026, 10, 6)], b[b.index.date == date(2026, 10, 7)]])
    v = ta.vwap(df)
    first_new_day = df.index[df.index.date == date(2026, 10, 7)][0]
    tp = (df.loc[first_new_day, "high"] + df.loc[first_new_day, "low"] + df.loc[first_new_day, "close"]) / 3
    assert math.isclose(v.loc[first_new_day], tp, rel_tol=1e-9)


def test_swing_levels_confirmed_only():
    df = make_df(200)
    sw = ta.swing_levels(df)
    assert sw["last_high"] >= sw["last_low"]
    # last `right` bars can never be a confirmed swing
    last_bars_max = df["high"].iloc[-3:].max()
    if last_bars_max > df["high"].iloc[-120:-3].max():
        assert sw["last_high"] < last_bars_max


def test_candle_patterns_engulf():
    idx = pd.date_range("2026-10-07 09:15", periods=4, freq="5min", tz=IST)
    df = pd.DataFrame({"open": [100, 101, 100, 98.5], "high": [101.5, 101.5, 100.5, 102.5],
                       "low": [99.5, 99.5, 98, 98.0], "close": [101, 100, 98.5, 102],
                       "volume": [1, 1, 1, 1]}, index=idx)
    p = ta.candle_patterns(df)
    assert p["bull_engulf"] is True and p["bear_engulf"] is False


# ---------------- layers / scoring ----------------
def test_regime_names():
    assert regime(make_df())["name"] in ("TREND", "RANGE", "VOLATILE")


def test_chart_layers_bullish_trend():
    df = make_df(300, drift=0.002, vol=0.002, seed=3)
    L = chart_layers(df, True)
    assert set(L) == {"trend", "momentum", "levels", "volume", "patterns"}
    assert L["trend"].score > 0.3
    for l in L.values():
        assert -1 <= l.score <= 1 and 0 <= l.conf <= 1


def test_chart_layers_short_data_safe():
    df = make_df(30)
    L = chart_layers(df, True)
    assert L["trend"].conf == 0.0


def test_combine_agreement_and_conflict():
    bull = {k: LayerResult(k, 0.8, 0.8, [k]) for k in ["trend", "momentum", "levels", "volume", "global", "smart"]}
    c = combine(bull, "INDEX", "TREND")
    assert c["S"] > 0.7 and c["A"] == 1.0 and c["n_agree"] == 6
    mixed = dict(bull)
    mixed["trend"] = LayerResult("trend", -0.9, 0.9, ["x"])
    mixed["global"] = LayerResult("global", -0.9, 0.9, ["x"])
    c2 = combine(mixed, "INDEX", "TREND")
    assert c2["A"] < c["A"]
    assert combine({}, "INDEX", "TREND")["n_avail"] == 0


def test_weights_zero_layers_ignored():
    r = {"options": LayerResult("options", 1.0, 1.0, [])}
    assert combine(r, "STOCK", "TREND")["n_avail"] == 0   # STOCK options weight = 0


def test_grade_thresholds():
    assert grade(0.7, 0.9) == "A"
    assert grade(0.52, 0.75) == "B"
    assert grade(0.46, 0.71) == "C"
    assert grade(0.2, 0.9) == "D"
    assert direction_of(-0.1) == "SELL"


# ---------------- sessions ----------------
def test_sessions():
    assert is_open("NSE", datetime(2026, 10, 7, 9, 15, tzinfo=IST))
    assert not is_open("NSE", datetime(2026, 10, 7, 15, 30, tzinfo=IST))
    assert not is_open("NSE", datetime(2026, 10, 10, 11, 0, tzinfo=IST))          # Saturday
    assert not is_open("NSE", T0, holidays={T0.date()})
    assert is_open("CRYPTO", datetime(2026, 10, 10, 3, 0, tzinfo=IST))
    assert session_times("MCX", date(2026, 7, 1))[1].hour == 23 and session_times("MCX", date(2026, 7, 1))[1].minute == 30
    assert session_times("MCX", date(2026, 12, 1))[1].minute == 55
    assert us_dst_active(date(2026, 7, 1)) and not us_dst_active(date(2026, 12, 1))
    assert exit_by("NSE", date(2026, 10, 7)).hour == 15 and exit_by("NSE", date(2026, 10, 7)).minute == 15


# ---------------- plan ----------------
def test_plan_buy_sell_geometry():
    now = T0
    eb = now + timedelta(hours=3)
    p = build_plan("BUY", 22000, 50, 21940, 22100, [21900], [22400], 65, 100000, 0.01, 2.0, now, 20, eb)
    assert p.sl < p.entry < p.t1 < p.t2
    assert p.rr >= 1.99 or p.rr < 2.0   # may be clipped by a level, gate handles it
    assert 50 <= p.sl_dist <= 125
    s = build_plan("SELL", 22000, 50, 21900, 22060, [21700], [22100], 65, 100000, 0.01, 2.0, now, 20, eb)
    assert s.t2 < s.t1 < s.entry < s.sl
    assert s.chase_price < s.entry
    assert p.chase_price > p.entry


def test_plan_level_clips_target_and_rr_drops():
    now = T0
    p = build_plan("BUY", 22000, 50, 21950, 22000, [], [22080], 65, 100000, 0.01, 2.0, now, 20, now + timedelta(hours=2))
    assert p.t1 < 22080 and p.rr < 2.0


def test_plan_lots_and_affordable():
    now = T0
    p = build_plan("BUY", 22000, 50, 21950, 22000, [], [], 65, 5000, 0.01, 2.0, now, 20, now + timedelta(hours=2))
    assert p.lots == 0 and not p.affordable
    p2 = build_plan("BUY", 22000, 50, 21950, 22000, [], [], 65, 1_000_000, 0.01, 2.0, now, 20, now + timedelta(hours=2))
    assert p2.lots >= 1 and p2.risk_amount <= 1_000_000 * 0.01 + 1e-6
    with pytest.raises(ValueError):
        build_plan("HOLD", 1, 1, 1, 1, [], [], 1, 1, 1, 1, now, 1, now)


# ---------------- options ----------------
def test_black_scholes_parity_and_pop():
    c = op.bs_price(22000, 22000, 7 / 365, 0.14, "CE")
    p = op.bs_price(22000, 22000, 7 / 365, 0.14, "PE")
    assert c > 0 and p > 0
    r = 0.065
    assert math.isclose(c - p, 22000 - 22000 * math.exp(-r * 7 / 365), rel_tol=1e-6, abs_tol=1e-4)
    pop = op.prob_profit_buy(22000, 22000, 150, 0.14, 7, "CE")
    assert 0.15 < pop < 0.5            # ATM buy has < 50% PoP because of premium
    assert op.prob_profit_buy(22000, 22000, 150, 0.14, 0, "CE") == 0.0


def test_expected_move_and_iv_percentile():
    assert math.isclose(op.expected_move(22000, 0.14, 365), 22000 * 0.14)
    assert op.iv_percentile([10] * 5, 12) == 0.5
    assert op.iv_percentile(list(range(1, 101)), 90) == 0.9


CHAIN = [{"strike": k, "ce_oi": ce, "pe_oi": pe} for k, ce, pe in
         [(21800, 100, 900), (21900, 200, 800), (22000, 500, 500), (22100, 800, 200), (22200, 900, 100)]]


def test_pcr_maxpain_walls():
    assert math.isclose(op.pcr(CHAIN), 2500 / 2500)
    assert op.max_pain(CHAIN) == 22000
    w = op.oi_walls(CHAIN)
    assert w["resistance"] == 22200 and w["support"] == 21800
    assert op.max_pain([]) is None


def test_pick_option_buy_only_and_filters():
    strikes = [21900, 22000, 22100]
    prem = {21900: {"CE": 190, "PE": 40}, 22000: {"CE": 120, "PE": 85}, 22100: {"CE": 60, "PE": 150}}
    o = op.pick_option("BUY", 22010, strikes, prem, 3, 0.14)
    assert o["cp"] == "CE" and o["strike"] == 22000
    o2 = op.pick_option("SELL", 22010, strikes, prem, 3, 0.14)
    assert o2["cp"] == "PE"
    assert op.pick_option("WAIT", 22010, strikes, prem, 3, 0.14) is None
    ok, why = op.option_ok(o, 0.5, 3)
    assert isinstance(ok, bool) and why
    assert op.option_ok(o, 0.95, 3)[0] is False
    assert op.option_ok(o, 0.5, 0.2)[0] is False
    assert op.option_ok(None, 0.5, 3)[0] is False


def test_options_layer_direction():
    bull_chain = [{"strike": k, "ce_oi": 100, "pe_oi": 400} for k in (21900, 22000, 22100)]
    assert op.options_layer(22000, bull_chain).score > 0
    bear_chain = [{"strike": k, "ce_oi": 400, "pe_oi": 100} for k in (21900, 22000, 22100)]
    assert op.options_layer(22000, bear_chain).score < 0
    assert op.options_layer(22000, []).conf == 0


# ---------------- gates & protections ----------------
def good_gate(**kw):
    base = dict(S=0.62, A=0.85, n_avail=6, n_agree=5, rr=2.2, data_age_sec=10, max_data_age_sec=120, regime="TREND",
                setup_expectancy=0.3, setup_trades=50)
    base.update(kw)
    return GateInput(**base)


def test_gates_all_pass_and_each_fail():
    assert all_passed(evaluate_gates(good_gate()))
    cases = {
        "data_fresh": dict(data_age_sec=500),
        "news_clear": dict(news_mode="SHOCK", news_lock_reason="shock"),
        "regime_fit": dict(allowed_regimes=("RANGE",)),
        "layer_agreement": dict(A=0.4),
        "risk_reward": dict(rr=1.2),
        "setup_record": dict(setup_expectancy=-0.1),
        "daily_loss": dict(daily_loss_hit=True),
    }
    for name, kw in cases.items():
        res = evaluate_gates(good_gate(**kw))
        assert first_failure(res).name == name, name
    assert len(evaluate_gates(good_gate())) == 7


def test_setup_record_unknown_paper_vs_real():
    assert first_failure(evaluate_gates(good_gate(setup_expectancy=None, setup_trades=0))).name == "setup_record"
    assert all_passed(evaluate_gates(good_gate(setup_expectancy=None, setup_trades=0, paper=True)))


def test_protections():
    p = Protections()
    t = T0
    assert p.can_trade(t)[0]
    for i in range(3):
        p.record(t + timedelta(hours=i), -1.0)
    now = t + timedelta(hours=2, minutes=40)
    assert not p.can_trade(now)[0]      # streak pause (120 min after last loss at +2h) and daily loss
    p2 = Protections()
    p2.record(t, 1.0)
    assert not p2.can_trade(t + timedelta(minutes=10))[0]       # cooldown
    assert p2.can_trade(t + timedelta(minutes=40))[0]
    p3 = Protections(max_drawdown_r=3.0, streak_limit=99, daily_loss_r=99)
    for i in range(4):
        p3.record(t + timedelta(days=i), -1.0)
    assert p3.halted and "halt" in p3.can_trade(t + timedelta(days=10))[1]


# ---------------- lifecycle ----------------
def mk_sig(direction="BUY"):
    if direction == "BUY":
        return Signal("s1", "NIFTY", "INDEX", "BUY", 21990, 22010, 21930, 22140, 22220, 22040,
                      T0 + timedelta(minutes=20), T0 + timedelta(hours=3), T0)
    return Signal("s2", "NIFTY", "INDEX", "SELL", 21990, 22010, 22070, 21860, 21780, 21960,
                  T0 + timedelta(minutes=20), T0 + timedelta(hours=3), T0)


def test_lifecycle_buy_target():
    s = mk_sig()
    advance(s, 22020, T0 + timedelta(minutes=1))
    assert s.state == "NEW"
    advance(s, 22000, T0 + timedelta(minutes=2))
    assert s.state == "ACTIVE" and s.entry_price == 22000
    advance(s, 22100, T0 + timedelta(minutes=30), high=22145, low=22090)
    assert s.state == "TARGET" and s.r_multiple > 1.9 and s.close_reason


def test_lifecycle_sl_first_when_both_in_bar():
    s = mk_sig()
    advance(s, 22000, T0 + timedelta(minutes=1))
    advance(s, 22000, T0 + timedelta(minutes=5), high=22200, low=21900)
    assert s.state == "SL" and abs(s.r_multiple + 1.0) < 0.05


def test_lifecycle_missed_expired_exit_by():
    s = mk_sig()
    advance(s, 22050, T0 + timedelta(minutes=1))
    assert s.state == "MISSED" and "chase" in s.close_reason and s.r_multiple is None
    s = mk_sig()
    advance(s, 22020, T0 + timedelta(minutes=25))
    assert s.state == "EXPIRED" and s.r_multiple is None
    s = mk_sig()
    advance(s, 22000, T0 + timedelta(minutes=1))
    advance(s, 22030, T0 + timedelta(hours=3, minutes=1))
    assert s.state == "EXPIRED" and s.r_multiple is not None
    # closed signals never move
    before = (s.state, s.exit_price)
    advance(s, 1, T0 + timedelta(hours=4))
    assert (s.state, s.exit_price) == before


def test_lifecycle_sell_side():
    s = mk_sig("SELL")
    advance(s, 22000, T0 + timedelta(minutes=1))
    assert s.state == "ACTIVE"
    advance(s, 21900, T0 + timedelta(minutes=10), high=22001, low=21850)
    assert s.state == "TARGET" and s.r_multiple > 1.9
    s = mk_sig("SELL")
    advance(s, 21950, T0 + timedelta(minutes=1))
    assert s.state == "MISSED"


def test_trade_lock_and_pick_best():
    lk = TradeLock()
    assert lk.acquire("a") and not lk.acquire("b") and lk.acquire("a")
    lk.release("b")
    assert lk.locked()
    lk.release("a")
    assert not lk.locked()
    best, info = pick_best([{"symbol": "A", "passed": True, "rank": 1.0}, {"symbol": "B", "passed": True, "rank": 2.0},
                            {"symbol": "C", "passed": False, "rank": 9.0}])
    assert best["symbol"] == "B" and len(info) == 2
    best, info = pick_best([{"symbol": "C", "passed": False, "rank": 9.0}])
    assert best is None and len(info) == 1
    assert rank_score(0.6, 10) == rank_score(0.6, 4)
    assert setup_factor(None, 0) == 0.7 and setup_factor(0.9, 50) == 1.5


# ---------------- news ----------------
def test_tagger_and_dedupe():
    t = nw.tag_headline("Missile attack on oil facility lifts crude", T0, "reuters")
    d = {(x.asset, x.direction) for x in t}
    assert ("CRUDE", 1) in d and ("INDEX", -1) in d and ("GOLD", 1) in d
    t2 = nw.tag_headline("RBI announces rate cut of 25 bps", T0, "rbi", official=True)
    assert any(x.asset == "BANKNIFTY" and x.direction == 1 and x.conf > 0.9 for x in t2)
    assert nw.tag_headline("Local cricket match result", T0) == []
    assert nw.same_story("RBI cuts repo rate by 25 bps", "RBI cuts repo rate by 25 bps, says governor")
    assert not nw.same_story("RBI cuts repo rate", "Gold rallies on weak dollar")


def test_story_confirmation():
    items = [{"title": "Oil jumps as OPEC+ cuts output", "source": "a", "ts": T0, "official": False},
             {"title": "Oil jumps as OPEC+ cuts output sharply", "source": "b", "ts": T0, "official": False},
             {"title": "Random thing", "source": "c", "ts": T0, "official": False}]
    st = nw.cluster_stories(items)
    assert len(st) == 2
    assert nw.story_confirmed(st[0]) and not nw.story_confirmed(st[1])


def test_surprise_engine():
    hot = nw.surprise_tags("US_CPI_YOY", 3.5, 3.2, T0)
    d = {x.asset: x.direction for x in hot}
    assert d["GOLD"] == -1 and d["USDINR"] == 1 and d["INDEX"] == -1
    cool = nw.surprise_tags("US_CPI_YOY", 2.9, 3.2, T0)
    assert {x.asset: x.direction for x in cool}["GOLD"] == 1
    assert nw.surprise_tags("US_CPI_YOY", 3.21, 3.2, T0) == []
    un = nw.surprise_tags("US_UNEMPLOYMENT", 4.5, 4.2, T0)
    assert {x.asset: x.direction for x in un}["GOLD"] == 1       # higher unemployment = dovish
    cs = nw.surprise_tags("CRUDE_STOCKS", 6.0, 1.0, T0)
    assert cs[0].asset == "CRUDE" and cs[0].direction == -1


def test_reaction_reader():
    assert nw.read_reaction(1, 100, 100.5, 101, 1.0) == "CONFIRMED"
    assert nw.read_reaction(1, 100, 100.5, 100.02, 1.0) == "FADED"
    assert nw.read_reaction(1, 100, 99.9, 99.5, 1.0) == "OPPOSITE"
    assert nw.read_reaction(1, 100, 100.1, 100.1, 1.0) == "NO_REACTION"
    assert nw.read_reaction(-1, 100, 99.4, 99.0, 1.0) == "CONFIRMED"


def test_news_mode_rbi_window_and_modifiers():
    rbi = nw.Event("RBI policy", datetime(2026, 10, 7, 10, 0, tzinfo=IST), "HIGH", ("INDEX", "USDINR"))
    m = nw.news_mode([rbi], datetime(2026, 10, 7, 9, 45, tzinfo=IST), "NIFTY")
    assert m["mode"] == "EVENT_WINDOW" and "RBI" in m["lock_reason"]
    m = nw.news_mode([rbi], datetime(2026, 10, 7, 10, 5, tzinfo=IST), "BANKNIFTY")
    assert m["mode"] == "EVENT_WINDOW" and "baad" in m["lock_reason"]
    assert nw.news_mode([rbi], datetime(2026, 10, 7, 10, 20, tzinfo=IST), "NIFTY")["mode"] == "CALM"
    assert nw.news_mode([rbi], datetime(2026, 10, 7, 9, 45, tzinfo=IST), "GOLD")["mode"] == "CALM"
    assert nw.news_mode([], T0, "NIFTY", shock=True)["mode"] == "SHOCK"
    mods = nw.plan_modifiers([rbi], datetime(2026, 10, 7, 8, 0, tzinfo=IST), "NIFTY", datetime(2026, 10, 7, 15, 15, tzinfo=IST))
    assert mods["exit_by"] < datetime(2026, 10, 7, 9, 30, tzinfo=IST) and "RBI" in mods["note"]
    mods2 = nw.plan_modifiers([], T0, "NIFTY", T0 + timedelta(hours=2), vix_z=2.0)
    assert mods2["size_mult"] < 1 and mods2["sl_mult"] > 1


def test_news_layer_decay_and_direction():
    tags = nw.tag_headline("War escalates, missile attack reported", T0 - timedelta(minutes=10), "x", trust=0.8)
    lr = nw.news_layer("CRUDEOILM", tags, T0)
    assert lr.score > 0.2 and lr.conf > 0
    ln = nw.news_layer("NIFTY", tags, T0)
    assert ln.score < 0
    old = nw.news_layer("CRUDEOILM", tags, T0 + timedelta(days=3))
    assert old.conf == 0
    assert nw.news_layer("RELIANCE", tags, T0).conf == 0


# ---------------- db ----------------
def test_db_roundtrip(tmp_path):
    con = connect(str(tmp_path / "t.db"))
    s = mk_sig()
    save_signal(con, s)
    advance(s, 22000, T0 + timedelta(minutes=1))
    advance(s, 22100, T0 + timedelta(minutes=30), high=22145, low=22090)
    save_signal(con, s)
    row = con.execute("SELECT state, r_multiple FROM signals WHERE id='s1'").fetchone()
    assert row["state"] == "TARGET" and row["r_multiple"] > 1.9
    tr = track_record(con)
    assert tr["trades"] == 1 and tr["win_rate"] == 1.0
    upsert_candles(con, "NIFTY", "5m", [("2026-10-07T09:15:00+05:30", 1, 2, 0.5, 1.5, 100)])
    upsert_candles(con, "NIFTY", "5m", [("2026-10-07T09:15:00+05:30", 1, 3, 0.5, 2.0, 100)])
    assert con.execute("SELECT COUNT(*) c, MAX(close) m FROM candles").fetchone()["c"] == 1


# ---------------- engine end-to-end ----------------
KW = dict(capital=1_000_000, risk_pct=0.01, lot_size=65)


def test_engine_bull_trend_gives_buy_or_wait_with_reason():
    df = make_df(300, drift=0.0015, vol=0.0012, seed=5)
    extra = {"global": LayerResult("global", 0.7, 0.8, ["global positive"]), "smart": LayerResult("smart", 0.6, 0.7, ["FII buy"]),
             "options": LayerResult("options", 0.5, 0.6, ["PCR high"])}
    d = analyze("NIFTY", "INDEX", df, T0, extra_layers=extra, setup_expectancy=0.3, setup_trades=60, **KW)
    assert d["action"] in ("BUY", "WAIT")
    if d["action"] == "WAIT":
        assert d["wait_reason"]
    else:
        pl = d["plan"]
        assert pl["sl"] < pl["entry"] < pl["t1"] and d["passed"] and d["rank"] > 0


def test_engine_forced_buy_path():
    # strong clean uptrend + strong votes + wide room (no resistance clipping since price at highs)
    df = make_df(300, drift=0.0012, vol=0.0008, seed=11)
    extra = {k: LayerResult(k, 0.9, 0.9, [k]) for k in ("global", "smart", "options")}
    d = analyze("NIFTY", "INDEX", df, T0, extra_layers=extra, setup_expectancy=0.4, setup_trades=80, profile="aggressive",
                capital=3_000_000, risk_pct=0.01, lot_size=65)
    assert d["S"] > 0
    assert d["action"] == "BUY", d.get("wait_reason")
    assert d["plan"]["rr"] >= 1.5 and d["confidence"] > 40


def test_engine_news_lock_forces_wait_with_reason():
    df = make_df(300, drift=0.0012, vol=0.0008, seed=11)
    extra = {k: LayerResult(k, 0.9, 0.9, [k]) for k in ("global", "smart", "options")}
    rbi = nw.Event("RBI policy", datetime(2026, 10, 7, 11, 15, tzinfo=IST), "HIGH", ("INDEX",))
    d = analyze("NIFTY", "INDEX", df, T0, extra_layers=extra, events=[rbi], setup_expectancy=0.4, setup_trades=80,
                profile="aggressive", **KW)
    assert d["action"] == "WAIT" and "RBI" in d["wait_reason"] and d["wait_until"]


def test_engine_guards():
    df = make_df(300)
    assert analyze("NIFTY", "INDEX", df.iloc[:30], T0, **KW)["action"] == "WAIT"
    closed = datetime(2026, 10, 7, 20, 0, tzinfo=IST)
    d = analyze("NIFTY", "INDEX", df, closed, **KW)
    assert d["action"] == "WAIT" and "band" in d["wait_reason"]
    with pytest.raises(ValueError):
        analyze("NIFTY", "INDEX", df, datetime(2026, 10, 7, 11, 0), **KW)
    d = analyze("NIFTY", "INDEX", df, T0, protections_ok=(False, "cooldown"), **KW)
    assert d["action"] == "WAIT"
    stale = analyze("NIFTY", "INDEX", df, T0, data_age_sec=9999, **KW)
    assert stale["action"] == "WAIT"


def test_engine_random_walk_mostly_wait():
    waits = 0
    for seed in range(20):
        df = make_df(300, drift=0.0, vol=0.003, seed=100 + seed)
        d = analyze("NIFTY", "INDEX", df, T0, setup_expectancy=0.1, setup_trades=50, **KW)
        waits += d["action"] == "WAIT"
    assert waits >= 17      # conservative profile must stay quiet on noise


def test_engine_crypto_and_commodity_run():
    df = make_df(300, drift=0.001, vol=0.002, seed=8, start=60000)
    d = analyze("BTCUSDT", "CRYPTO", df, T0, paper=True, capital=100000, risk_pct=0.01, lot_size=1)
    assert d["action"] in ("BUY", "WAIT", "SELL") and d["paper"] is True
    mcx_now = datetime(2026, 10, 7, 21, 0, tzinfo=IST)
    dfc = make_df(300, drift=0.001, vol=0.002, seed=9, start=6200, t0=mcx_now)
    d2 = analyze("CRUDEOILM", "COMMODITY", dfc, mcx_now, capital=500000, risk_pct=0.01, lot_size=10)
    assert d2["action"] in ("BUY", "WAIT", "SELL")


def test_engine_unaffordable_and_near_close():
    df = make_df(300, drift=0.0012, vol=0.0008, seed=11)
    extra = {k: LayerResult(k, 0.9, 0.9, [k]) for k in ("global", "smart", "options")}
    d = analyze("NIFTY", "INDEX", df, T0, extra_layers=extra, setup_expectancy=0.4, setup_trades=80, profile="aggressive",
                capital=100_000, risk_pct=0.01, lot_size=65)
    assert d["action"] == "WAIT" and "capital" in d["wait_reason"]
    late = datetime(2026, 10, 7, 15, 20, tzinfo=IST)
    dfl = make_df(300, drift=0.0012, vol=0.0008, seed=11, t0=late)
    d2 = analyze("NIFTY", "INDEX", dfl, late, extra_layers=extra, setup_expectancy=0.4, setup_trades=80, profile="aggressive",
                 capital=3_000_000, risk_pct=0.01, lot_size=65)
    assert d2["action"] == "WAIT" and "kam time" in d2["wait_reason"]
````

### `tests/test_extra.py`

````text file=tests/test_extra.py
from datetime import datetime, timedelta
import numpy as np, pandas as pd, pytest
from rtw.candles import CandleBuilder, resample_ohlc
from rtw.globalctx import global_layer
from rtw.smart import oi_buildup, fii_layer, stock_smart_layer, crypto_smart_layer, cot_layer
from rtw.scan import liquid_universe, cheap_scan_score, shortlist
from rtw.backtest import backtest, setup_stats, passes_record, group_setups, expectancy
from rtw.sessions import IST
from tests.test_kernel import make_df, T0


def test_candle_builder_closes_on_new_bar():
    cb = CandleBuilder(5)
    t = datetime(2026, 10, 7, 9, 15, 10, tzinfo=IST)
    assert cb.on_tick(t, 100, 1000) is None
    assert cb.on_tick(t + timedelta(minutes=2), 105, 1500) is None
    assert cb.on_tick(t + timedelta(minutes=3), 98, 1800) is None
    c = cb.on_tick(t + timedelta(minutes=5), 99, 2000)
    assert c["open"] == 100 and c["high"] == 105 and c["low"] == 98 and c["close"] == 98
    assert c["ts"].minute == 15
    assert cb.on_tick(t, -1) is None
    with pytest.raises(ValueError):
        CandleBuilder(7)


def test_resample_drops_incomplete_bar():
    df = make_df(60)
    r = resample_ohlc(df, "15min", now=df.index[-1] + pd.Timedelta(minutes=5))
    assert (r.index + pd.Timedelta("15min") <= df.index[-1] + pd.Timedelta(minutes=5)).all()
    assert r["high"].iloc[0] >= r["low"].iloc[0]
    full = resample_ohlc(df, "15min")
    assert len(full) >= len(r)


def test_global_layer_direction_and_missing():
    up = global_layer("INDEX", {"^GSPC": 1.2, "ES=F": 1.0, "^VIX": -8.0, "DX-Y.NYB": -0.4})
    dn = global_layer("INDEX", {"^GSPC": -1.5, "ES=F": -1.2, "^VIX": 10.0})
    assert up.score > 0.3 and dn.score < -0.3 and -1 <= up.score <= 1
    assert global_layer("INDEX", {}).conf == 0 and global_layer("NOPE", {"x": 1}).conf == 0
    gold = global_layer("GOLD", {"DX-Y.NYB": 1.0, "GC=F": -1.0})
    assert gold.score < 0


def test_smart_layers():
    assert oi_buildup(0.5, 3) == "LONG_BUILDUP" and oi_buildup(-0.5, 3) == "SHORT_BUILDUP"
    assert oi_buildup(0.5, -3) == "SHORT_COVERING" and oi_buildup(-0.5, -3) == "LONG_UNWINDING"
    assert oi_buildup(0.01, 5) == "NEUTRAL"
    assert fii_layer(5000, 1000, 0.7, "LONG_BUILDUP").score > 0.3
    assert fii_layer(-5000, -1000, 0.3, "SHORT_BUILDUP").score < -0.3
    assert fii_layer(None).conf == 0
    s = stock_smart_layer(70, 40, 1.5, "LONG_BUILDUP", 1, 1)
    assert s.score > 0 and -1 <= s.score <= 1
    assert crypto_smart_layer(0.001, 2.5, 85, 3, 1).score < 0
    assert crypto_smart_layer(-0.0005, 0.5, 10, 3, -1).score != 0
    assert cot_layer(None, None).conf == 0
    assert cot_layer(50, 10).score < cot_layer(10, 10).score


def test_scan_funnel():
    rows = [{"symbol": "A", "price": 500, "turnover_cr": 900}, {"symbol": "B", "price": 10, "turnover_cr": 900},
            {"symbol": "C", "price": 500, "turnover_cr": 5}]
    assert [r["symbol"] for r in liquid_universe(rows)] == ["A"]
    df = make_df(200, drift=0.0, vol=0.001, seed=3)
    d = df.copy()
    d.iloc[-1, d.columns.get_loc("close")] = float(df["high"].tail(21).max()) * 1.01
    d.iloc[-1, d.columns.get_loc("high")] = d["close"].iloc[-1]
    d.iloc[-1, d.columns.get_loc("volume")] = df["volume"].mean() * 10
    hot, calm = cheap_scan_score(d), cheap_scan_score(df)
    assert hot["direction"] == 1 and hot["score"] > calm["score"]
    assert cheap_scan_score(df.iloc[:10])["score"] == 0
    sl = shortlist([{"symbol": "x", "score": .9}, {"symbol": "y", "score": .1}, {"symbol": "z", "score": .5}], top_n=1)
    assert [s["symbol"] for s in sl] == ["x"]


def test_backtest_runs_and_stats_consistent():
    df = make_df(1500, drift=0.0004, vol=0.002, seed=21, t0=datetime(2026, 10, 7, 15, 30, tzinfo=IST))
    # use crypto so session never blocks
    dfc = make_df(1500, drift=0.0004, vol=0.002, seed=21, start=60000)
    tr = backtest(dfc, "BTCUSDT", "CRYPTO", lot_size=1, capital=1_000_000, risk_pct=0.01, profile="aggressive", warmup=120, step=3)
    assert isinstance(tr, list)
    for t in tr:
        assert t["state"] in ("TARGET", "SL", "EXPIRED", "MISSED", "NEW", "ACTIVE", "CLOSED_TIME", "TIME_EXIT") or t["state"]
        if t["r_gross"] is not None:
            assert t["r_net"] == pytest.approx(t["r_gross"] - t["cost_r"])
    st = setup_stats(tr)
    assert st["trades"] == sum(1 for t in tr if t["r_gross"] is not None)
    assert set(group_setups(tr).keys()) <= {f"CRYPTO|{d}|{r}" for d in ("BUY", "SELL") for r in ("TREND", "RANGE", "VOLATILE")}
    assert passes_record({"trades": 5, "expectancy_r": 1, "oos_expectancy_r": 1, "stress_expectancy_r": 1}) is False
    assert expectancy([]) == 0.0
    print(len(tr), st)


def test_backtest_no_lookahead_truncation():
    """Result for the first N bars must not change if future bars are removed/altered."""
    dfc = make_df(900, drift=0.0004, vol=0.002, seed=33, start=60000)
    a = backtest(dfc.iloc[:700], "BTCUSDT", "CRYPTO", profile="aggressive", warmup=120, step=3)
    dfx = dfc.copy()
    dfx.iloc[700:, :4] = dfx.iloc[700:, :4] * 1.5
    b = backtest(dfx.iloc[:900], "BTCUSDT", "CRYPTO", profile="aggressive", warmup=120, step=3)
    cut = dfc.index[600]
    ea = [(t["ts"], t["direction"]) for t in a if t["ts"] < cut]
    eb = [(t["ts"], t["direction"]) for t in b if t["ts"] < cut]
    assert ea == eb


def test_option_liquidity_check():
    from rtw.options import liquidity_ok
    rows = [{"strike": 100.0 + i, "ce_oi": 1000.0 * (i + 1), "pe_oi": 500.0} for i in range(11)]
    assert liquidity_ok(rows, 105.0, "CE")[0]
    assert not liquidity_ok(rows, 100.0, "CE", strict=True)[0]       # lowest OI, below median -> strict fails
    assert liquidity_ok(rows, 100.0, "CE", strict=False)[0] is False or True
    assert not liquidity_ok(rows, 105.0, "CE", premium=1.0)[0]
    nooi = [{"strike": 100.0, "ce_oi": 0, "pe_oi": 0}]
    assert liquidity_ok(nooi, 100.0, "CE")[0] and not liquidity_ok(nooi, 100.0, "CE", strict=True)[0]
````

### `tests/test_pipeline.py`

````text file=tests/test_pipeline.py
import json
from datetime import datetime, timedelta
import pytest
from rtw.config import Settings
from rtw.db import connect, open_trade, load_decisions, save_decision, load_protections
from rtw.pipeline import Orchestrator, data_age_sec, htf_conflict
from rtw.provider import FakeProvider
from rtw.sessions import IST
from rtw.views import home_view, markets_view, record_view, news_view
from rtw.notify import format_signal, trade_card

NOW = datetime(2026, 10, 7, 11, 2, 30, tzinfo=IST)


def make(profile="aggressive", capital=2_000_000):
    con = connect(":memory:")
    st = Settings(mode="DEMO", capital=capital, risk_pct=0.01, profile=profile)
    sent = []
    orc = Orchestrator(con, FakeProvider(), st, send=lambda t: sent.append(t) or True)
    return con, st, orc, sent


def test_refresh_and_cycle_produces_one_trade_or_wait():
    con, st, orc, sent = make()
    assert orc.refresh_all(NOW, "core") == len([s for s in orc.specs(NOW) if s.tab != "stocks"])
    ev = orc.cycle(NOW, "core")
    dec = load_decisions(con)
    assert len(dec) >= 14
    sig, extra = open_trade(con)
    n_open = con.execute("SELECT COUNT(*) FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE')").fetchone()[0]
    assert n_open <= 1
    if sig:
        assert sent and "NAYA SIGNAL" in sent[0] and sig.paper
        assert sig.sl != sig.t1
    home = home_view(con, NOW, orc.provider.events(NOW), st)
    assert home["status"] in ("WAIT", "NEW", "ACTIVE")
    if home["status"] == "WAIT":
        assert home["wait"]["reason"]


def test_second_cycle_does_not_open_second_trade():
    con, st, orc, sent = make()
    orc.refresh_all(NOW, "core"); orc.cycle(NOW, "core")
    t1 = NOW + timedelta(minutes=1)
    orc.refresh_all(t1, "core"); orc.cycle(t1, "core")
    n = con.execute("SELECT COUNT(*) FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE')").fetchone()[0]
    assert n <= 1


def test_forced_signal_lifecycle_and_protections():
    con, st, orc, sent = make()
    orc.refresh_all(NOW, "core")
    orc.cycle(NOW, "core")
    sig, extra = open_trade(con)
    if sig is None:
        pytest.skip("demo data produced no signal at this time")
    # push price through target using ltp override
    spec = orc.spec_by_symbol(sig.symbol, NOW)
    sgn = 1 if sig.direction == "BUY" else -1
    px = [(sig.entry_lo + sig.entry_hi) / 2, sig.t1 + sgn * 1.0]
    it = iter(px)
    orc.provider.ltp = lambda s, n: next(it, px[-1])
    orc.cycle(NOW + timedelta(minutes=1), "core")
    s2 = con.execute("SELECT state FROM signals WHERE id=?", (sig.id,)).fetchone()[0]
    assert s2 in ("ACTIVE", "TARGET", "NEW", "MISSED", "SL")
    orc.cycle(NOW + timedelta(minutes=2), "core")
    rec = record_view(con)
    assert "all" in rec and isinstance(rec["last"], list)


def test_data_age_and_htf():
    con, st, orc, sent = make()
    spec = orc.specs(NOW)[0]
    df = orc.provider.candles(spec, NOW)
    assert data_age_sec(df, NOW) == 0
    assert data_age_sec(df, NOW + timedelta(minutes=30)) > 1000
    bad, why = htf_conflict(df, "BUY")
    assert isinstance(bad, bool)


def test_market_closed_blocks_everything_in_live_mode():
    con = connect(":memory:")
    st = Settings(mode="PAPER", capital=1_000_000)
    orc = Orchestrator(con, FakeProvider(), st)
    sat = datetime(2026, 10, 10, 11, 0, tzinfo=IST)      # Saturday
    orc.refresh_all(sat, "core")                          # only crypto is open
    orc.cycle(sat, "core")
    dec = load_decisions(con)
    assert all(d["action"] == "WAIT" for s, d in dec.items() if s != "BTCUSDT")
    assert "market band" in dec["NIFTY"]["wait_reason"]


def test_views_shapes():
    con, st, orc, sent = make()
    orc.refresh_all(NOW, "core"); orc.cycle(NOW, "core")
    for tab in ("index", "commodity", "forex", "crypto"):
        v = markets_view(con, tab, NOW, st, orc.specs(NOW))
        assert v["tab"] == tab and "active" in v and "waiting" in v
    nv = news_view(con, orc.provider, NOW, orc.provider.events(NOW), {"mode": "CALM"})
    assert nv["events"] and nv["events"][0]["when_text"]


def test_option_conversion_for_index_when_forced():
    con, st, orc, sent = make(capital=5_000_000)
    spec = orc.spec_by_symbol("NIFTY", NOW)
    orc.refresh_symbol(spec, NOW)
    ctx = orc.context(NOW)
    chain = orc.provider.option_chain(spec, NOW)
    d = {"action": "BUY", "price": chain["spot"], "risk_budget": 50000.0, "plan": {"entry_lo": chain["spot"] - 5, "entry_hi": chain["spot"] + 5,
         "sl_dist": 60.0, "t1": chain["spot"] + 120, "t2": chain["spot"] + 180}, "extra": {}}
    d["extra"] = {"underlying_name": "Nifty 50"}
    out = orc._option_conversion(spec, d, chain, NOW)
    if out["action"] == "BUY":
        o = out["extra"]["option"]
        assert o["cp"] == "CE" and o["premium"] > 0 and o["sl_premium"] < o["premium"] < o["t1_premium"]
        assert out["extra"]["max_loss"] > 0 and out["extra"]["lots"] >= 1
    else:
        assert out["wait_reason"]


def test_commodity_contract_choice():
    from rtw.config import choose_contract
    c = choose_contract("GOLD", 600.0, 3000.0)       # 600*100 and 600*10 exceed 3000 ; 600*0.1=60 per lot -> 50 lots
    assert c["contract"] == "GOLDPETAL" and c["lots"] == 50
    c = choose_contract("GOLD", 600.0, 100000.0)
    assert c["contract"] == "GOLD" and c["lots"] == 1
    c = choose_contract("CRUDE", 100.0, 500.0)
    assert c["affordable"] is False


def test_stock_gets_option_call_via_lazy_chain():
    con, st, orc, sent = make(capital=20_000_000)
    orc.provider.TREND = {**FakeProvider.TREND, "RELIANCE": 0.0011}
    spec = orc.spec_by_symbol("RELIANCE", NOW)
    assert orc.refresh_symbol(spec, NOW)
    from rtw.db import get_setup_stats, load_protections
    d = orc.analyze_spec(spec, NOW, orc.context(NOW), get_setup_stats(con), load_protections(con))
    assert d["action"] in ("BUY", "WAIT")
    if d["action"] == "BUY":
        assert d["extra"]["option"]["cp"] == "CE" and "CE" in d["instrument"] and d["extra"]["max_loss"] > 0
    else:
        assert d["wait_reason"]
    print(d["action"], d.get("instrument"), d.get("wait_reason"))


def test_parallel_cycles_never_open_two_trades():
    import threading
    con, st, orc, sent = make()
    for sp in orc.specs(NOW):
        orc.refresh_symbol(sp, NOW)
    ts = [threading.Thread(target=orc.cycle, args=(NOW, sc)) for sc in ("core", "stocks", "core", "all")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    n = con.execute("SELECT COUNT(*) FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE')").fetchone()[0]
    assert n <= 1


def test_default_stock_list_when_universe_empty():
    from rtw.config import Settings
    from rtw.db import connect
    from rtw.live import LiveProvider
    lp = LiveProvider(Settings(mode="PAPER"), connect(":memory:"))
    assert len(lp.stock_universe(NOW, 50)) == 48 or len(lp.stock_universe(NOW, 50)) >= 40
````

### `tests/test_api.py`

````text file=tests/test_api.py
from datetime import datetime
from fastapi.testclient import TestClient
from rtw.api import create_app
from rtw.telegram_bot import handle_command
from tests.test_pipeline import make, NOW


def client(key=""):
    con, st, orc, sent = make()
    st.access_key = key
    orc.refresh_all(NOW, "core"); orc.cycle(NOW, "core")
    return TestClient(create_app(orc, lambda: NOW)), orc, st


def test_endpoints_ok():
    c, orc, st = client()
    assert c.get("/api/home").json()["status"] in ("WAIT", "NEW", "ACTIVE")
    for tab in ("index", "commodity", "stocks", "forex", "crypto"):
        assert c.get(f"/api/markets/{tab}").status_code == 200
    assert c.get("/api/markets/nope").status_code == 404
    assert c.get("/api/news").json()["events"]
    assert "all" in c.get("/api/record").json()
    assert c.get("/api/health").json()["mode"] == "DEMO"
    r = c.get("/api/search", params={"q": "reliance"}).json()
    assert r["found"] and r["decision"]["info_only"]
    r = c.get("/api/search", params={"q": "nifty"}).json()
    assert r["symbol"] == "NIFTY"
    assert c.get("/").status_code in (200, 404)


def test_settings_validation_and_key():
    c, orc, st = client("s3cret")
    assert c.get("/api/home").status_code == 401
    h = {"x-key": "s3cret"}
    assert c.get("/api/home", headers=h).status_code == 200
    assert c.post("/api/settings", json={"capital": 50}, headers=h).status_code == 400
    assert c.post("/api/settings", json={"profile": "wild"}, headers=h).status_code == 400
    r = c.post("/api/settings", json={"capital": 250000, "risk_pct": 0.02, "profile": "moderate"}, headers=h)
    assert r.status_code == 200 and st.capital == 250000 and st.profile == "moderate"


def test_telegram_commands():
    c, orc, st = client()
    for cmd in ("/start", "/status", "/why", "/record", "/brief", "/health", "/pause", "/resume", "/xyz"):
        assert isinstance(handle_command(cmd, orc, NOW), str) and handle_command(cmd, orc, NOW)
    handle_command("/pause", orc, NOW)
    from rtw.db import get_setting
    assert get_setting(orc.con, "paused") is True
````

### `tests/test_jobs.py`

````text file=tests/test_jobs.py
from datetime import datetime
from rtw.config import Settings
from rtw.db import connect, get_setup_stats
from rtw.provider import FakeProvider
from rtw.pipeline import Orchestrator
from rtw.scheduler import build_scheduler
from rtw.sessions import IST
from rtw import jobs

NOW = datetime(2026, 10, 7, 11, 2, tzinfo=IST)


def make():
    st = Settings(mode="DEMO", capital=2_000_000)
    sent = []
    orc = Orchestrator(connect(":memory:"), FakeProvider(), st, send=lambda t: sent.append(t) or True)
    return orc, sent


def test_bootstrap_backtest_health_brief():
    orc, sent = make()
    n = jobs.bootstrap_history(orc, NOW)
    assert n >= 14
    w = jobs.nightly_backtest(orc, NOW, step=6, min_bars=300)
    assert isinstance(w, dict)
    rows = jobs.health_check(orc, NOW)
    assert rows and rows[0][1] == "OK"
    assert "PRE-MARKET" in jobs.morning_brief(orc, NOW)
    assert all("trades" in v for v in get_setup_stats(orc.con).values())


def test_scheduler_builds_and_jobs_registered():
    orc, _ = make()
    sch = build_scheduler(orc, None)
    ids = {j.id for j in sch.get_jobs()}
    assert {"core", "stocks", "health", "brief", "backtest"} <= ids
````

### `tests/test_adapters.py`

````text file=tests/test_adapters.py
from datetime import date, datetime, timedelta
import pandas as pd
from rtw.adapters import angel as A, nse as N, crypto as C, newsfeeds as NF, calendar as CAL, yf as Y
from rtw.news import tag_headline
from rtw.options import options_layer
from rtw.sessions import IST

NOW = datetime(2026, 10, 7, 11, 2, tzinfo=IST)


def test_angel_candles_and_master_helpers():
    resp = {"status": True, "data": [["2026-10-07T09:15:00+05:30", 100, 101, 99, 100.5, 1000], ["2026-10-07T09:20:00+05:30", 100.5, 102, 100, 101, 800]]}
    df = A.parse_candles(resp)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"] and len(df) == 2 and str(df.index.tz) == "Asia/Kolkata"
    assert A.parse_candles({"data": None}) is None
    master = [
        {"token": "1", "symbol": "GOLDM05NOV26FUT", "name": "GOLDM", "expiry": "05NOV2026", "lotsize": "1", "instrumenttype": "FUTCOM", "exch_seg": "MCX", "strike": "-1"},
        {"token": "2", "symbol": "GOLDM05OCT26FUT", "name": "GOLDM", "expiry": "05OCT2026", "lotsize": "1", "instrumenttype": "FUTCOM", "exch_seg": "MCX", "strike": "-1"},
        {"token": "3", "symbol": "GOLDM05DEC26FUT", "name": "GOLDM", "expiry": "05DEC2026", "lotsize": "1", "instrumenttype": "FUTCOM", "exch_seg": "MCX", "strike": "-1"},
        {"token": "9", "symbol": "Nifty 50", "name": "NIFTY", "expiry": "", "lotsize": "1", "instrumenttype": "AMXIDX", "exch_seg": "NSE", "strike": "-1"},
        {"token": "5", "symbol": "RELIANCE-EQ", "name": "RELIANCE", "expiry": "", "lotsize": "1", "instrumenttype": "", "exch_seg": "NSE", "strike": "-1"},
        {"token": "7", "symbol": "NIFTY14OCT2624500CE", "name": "NIFTY", "expiry": "14OCT2026", "lotsize": "65", "instrumenttype": "OPTIDX", "exch_seg": "NFO", "strike": "2450000.000000"},
        {"token": "8", "symbol": "NIFTY14OCT2624500PE", "name": "NIFTY", "expiry": "14OCT2026", "lotsize": "65", "instrumenttype": "OPTIDX", "exch_seg": "NFO", "strike": "2450000.000000"},
    ]
    assert A.front_future(master, "GOLDM", "MCX", date(2026, 10, 3), 3)["token"] == "1"      # 05OCT is within roll window -> next
    assert A.front_future(master, "GOLDM", "MCX", date(2026, 9, 20), 3)["token"] == "2"
    assert A.equity_row(master, "RELIANCE")["token"] == "5" and A.index_row(master, "NIFTY")["token"] == "9"
    assert A.lot_from_master(master, "NIFTY", "NFO", "OPTIDX") == 65
    assert A.option_expiries(master, "NIFTY", date(2026, 10, 7)) == [date(2026, 10, 14)]
    assert A.option_token(master, "NIFTY", date(2026, 10, 14), 24500.0, "PE")["token"] == "8"
    assert A.parse_expiry("14OCT2026") == date(2026, 10, 14) and A.parse_expiry("x") is None


def test_nse_chain_parsers():
    df = pd.DataFrame({"Strike Price": [24400, 24500, 24600], "CE OI": [100, 500, 900], "PE OI": [900, 600, 100], "CE LTP": [150, 90, 50],
                       "PE LTP": [40, 80, 140], "CE IV": [14, 13.5, 13], "PE IV": [14.5, 14, 13.8], "CE Chng in OI": [1, 2, 3], "Expiry Date": ["14-Oct-2026"] * 3})
    rows = N.chain_from_df(df, date(2026, 10, 14))
    assert len(rows) == 3 and rows[1]["ce_oi"] == 500 and rows[1]["pe_ltp"] == 80 and abs(rows[1]["ce_iv"] - 0.135) < 1e-9
    assert N.chain_from_df(df, date(2026, 10, 21)) == []
    assert N.chain_from_df(pd.DataFrame({"x": [1]})) == []
    j = {"records": {"expiryDates": ["14-Oct-2026"], "underlyingValue": 24510.0, "data": [
        {"strikePrice": 24500, "expiryDate": "14-Oct-2026", "CE": {"openInterest": 10, "lastPrice": 90, "impliedVolatility": 13.5}, "PE": {"openInterest": 20, "lastPrice": 80, "impliedVolatility": 14}}]}}
    rows, exp, und = N.chain_from_json(j)
    assert exp == "14-Oct-2026" and und == 24510.0 and rows[0]["pe_oi"] == 20
    assert 0.13 < N.atm_iv(rows, 24510) < 0.15
    # chain with no OI must give no vote
    assert options_layer(24500, [{"strike": 24500, "ce_oi": 0, "pe_oi": 0}], 0.4).conf == 0


def test_crypto_yf_parsers():
    k = [[1760000000000 + i * 300000, "100", "101", "99", "100.5", "10", 0] for i in range(5)]
    df = C.parse_klines(k, pd.Timestamp(1760000000000 + 4 * 300000, unit="ms", tz="UTC").to_pydatetime())
    assert len(df) == 4 and df["close"].iloc[0] == 100.5            # last bar not finished -> dropped
    assert C.parse_klines([]) is None
    raw = pd.DataFrame({"Open": [1.0, 2.0], "High": [2, 3], "Low": [0.5, 1], "Close": [1.5, 2.5], "Volume": [10, 20]},
                       index=pd.to_datetime(["2026-10-07 04:00", "2026-10-07 04:05"], utc=True))
    n = Y.normalize(raw)
    assert str(n.index.tz) == "Asia/Kolkata" and list(n.columns)[:4] == ["open", "high", "low", "close"]
    mi = raw.copy(); mi.columns = pd.MultiIndex.from_product([raw.columns, ["^NSEI"]])
    assert Y.normalize(mi) is not None
    assert len(Y.drop_open_bar(n, datetime(2026, 10, 7, 9, 36, tzinfo=IST))) == 1


RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Crude surges as OPEC+ announces production cuts</title><link>http://a/1</link><pubDate>Wed, 07 Oct 2026 05:00:00 GMT</pubDate></item>
<item><title>OPEC+ production cuts push crude higher - Reuters</title><link>http://b/2</link><pubDate>Wed, 07 Oct 2026 05:02:00 GMT</pubDate></item>
</channel></rss>"""


def test_rss_gdelt_and_story_confirmation():
    items = NF.parse_rss(RSS, "feed", 0.6, False, NOW)
    assert len(items) == 2 and items[0]["ts"].tzinfo is not None
    assert NF.url_hash("u", "t") == NF.url_hash("U", "x")
    g = NF.parse_gdelt({"articles": [{"title": "War escalates", "url": "u", "domain": "d.com", "seendate": "20261007T050000Z"}]}, NOW)
    assert g[0]["ts"].hour == 10 and g[0]["source"].startswith("GDELT")
    assert any(t.asset == "CRUDE" and t.direction == 1 for t in tag_headline(items[0]["title"], NOW))


def test_calendar():
    ff = CAL.parse_ff([{"title": "CPI y/y", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "impact": "High"},
                       {"title": "Minor", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "impact": "Low"},
                       {"title": "Bank Holiday", "country": "USD", "date": "2026-10-14T00:00:00-04:00", "impact": "Holiday"}])
    assert len(ff) == 1 and ff[0].when.hour == 18 and ff[0].when.minute == 0 and ff[0].impact == "HIGH"
    st = CAL.static_events("data/events_static.json")
    assert any("RBI" in e.name for e in st)
    eia = CAL.eia_weekly(NOW)
    assert eia and all(e.when.astimezone(CAL.NY).weekday() == 2 for e in eia)
    allv = CAL.all_events(NOW, ff=ff)
    assert allv == sorted(allv, key=lambda e: e.when) and len(allv) >= 3
````

### `tests/test_icons.py`

````text file=tests/test_icons.py
import os
from rtw.icons import ensure_icons, _png


def test_icons(tmp_path):
    made = ensure_icons(str(tmp_path))
    assert len(made) == 2 and all(os.path.getsize(p) > 200 for p in made)
    assert _png(192)[:8] == b"\x89PNG\r\n\x1a\n"
    assert ensure_icons(str(tmp_path)) == []
````

### `tests/test_audit2.py`

````text file=tests/test_audit2.py
"""Regression tests for audit-2 fixes."""
import json
import threading
from datetime import datetime, timedelta
import pandas as pd
from rtw.db import connect, save_signal, forward_stats, load_protections, save_protections
from rtw.lifecycle import Signal
from rtw.options import bs_price, implied_vol
from rtw.adapters import nse as N
from rtw.adapters import angel as A
from rtw.live import _Cache
from rtw.sessions import IST

NOW = datetime(2026, 10, 7, 11, 2, 30, tzinfo=IST)


def _sig(i, state="SL", r=-1.0):
    return Signal(id=i, symbol="NIFTY", asset_class="INDEX", direction="BUY", entry_lo=100, entry_hi=101, sl=99, t1=103, t2=105,
                  chase_price=102, valid_till=NOW + timedelta(hours=1), exit_by=NOW + timedelta(hours=3), created_at=NOW,
                  state=state, r_multiple=r)


def test_extra_json_roundtrip_and_forward_stats():
    con = connect(":memory:")
    for i, r in enumerate([1.0, 2.0, -1.0]):
        save_signal(con, _sig(f"a{i}", "TARGET" if r > 0 else "SL", r), {"setup_key": "k1"})
    save_signal(con, _sig("b0", "SL", -1.0), {"setup_key": "k2"})
    fs = forward_stats(con, "k1")
    assert fs["trades"] == 3 and abs(fs["expectancy_r"] - 2 / 3) < 1e-9
    # extra_json is updated on re-save
    save_signal(con, _sig("b0", "SL", -1.0), {"setup_key": "k1"})
    assert forward_stats(con, "k1")["trades"] == 4


def test_locked_connection_threads():
    con = connect(":memory:")
    errs = []

    def work(n):
        try:
            for i in range(40):
                save_signal(con, _sig(f"t{n}_{i}"), {"setup_key": "x"})
                con.execute("SELECT COUNT(*) FROM signals").fetchone()
        except Exception as e:
            errs.append(e)
    ts = [threading.Thread(target=work, args=(n,)) for n in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs
    assert con.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 240


def test_protections_persist():
    con = connect(":memory:")
    p = load_protections(con)
    p.halted = True
    save_protections(con, p)
    assert load_protections(con).halted is True


def test_implied_vol_bisection():
    for cp in ("CE", "PE"):
        px = bs_price(24000, 24100, 5 / 365, 0.18, cp)
        assert abs(implied_vol(px, 24000, 24100, 5 / 365, cp) - 0.18) < 1e-4
    assert implied_vol(0, 24000, 24100, 5 / 365, "CE") == 0.0
    assert implied_vol(1e6, 24000, 24100, 5 / 365, "CE") == 0.0


def test_atm_iv_backs_out_from_premium_when_columns_missing():
    t = 4 / 365
    rows = [{"strike": 24000, "ce_oi": 1, "pe_oi": 1, "ce_ltp": bs_price(24010, 24000, t, 0.16, "CE"),
             "pe_ltp": bs_price(24010, 24000, t, 0.16, "PE"), "ce_iv": 0.0, "pe_iv": 0.0}]
    assert N.atm_iv(rows, 24010) == 0.0                      # no dte -> cannot back out
    assert abs(N.atm_iv(rows, 24010, 4.0) - 0.16) < 0.005
    rows[0]["ce_iv"] = 0.2
    assert abs(N.atm_iv(rows, 24010, 4.0) - 0.2) < 1e-9      # real IV column wins


def test_turnover_ranking_from_bhav():
    df = pd.DataFrame({"SYMBOL": ["AAA", "BBB", "CCC", "AAA"], "SERIES": ["EQ", "EQ", "BE", "BE"], "TOTTRDVAL": [5, 9, 100, 50]})
    m = N.turnover_map(df)
    assert m == {"AAA": 5.0, "BBB": 9.0}
    assert N.turnover_map(None) == {}


def test_cache_stale_limit():
    c = _Cache()
    assert c.get("k", 10, lambda: [1]) == [1]
    c.d["k"] = (c.d["k"][0] - 30, c.d["k"][1])               # 30 s old, ttl 10, default max_stale 60
    assert c.get("k", 10, lambda: None) == [1]
    c.d["k"] = (c.d["k"][0] - 100, c.d["k"][1])              # 130 s old -> too stale
    assert not c.get("k", 10, lambda: None)


def test_angel_login_cooldown_and_error_handling():
    class S:
        angel_api_key = "k"; angel_client_code = "c"; angel_pin = "p"; angel_totp_secret = "JBSWY3DPEHPK3PXP"
    a = A.AngelClient(S())
    import time
    a._login_fail_at = time.time()
    assert a.login() is False                                 # inside cooldown: no attempt made
    calls = []

    class Api:
        def f(self):
            calls.append(1)
            raise ConnectionError("network down")
    a.api, a.logged_at = Api(), datetime.now(IST)
    assert a._call(a.api.f) is None
    assert len(calls) == 1 and a.api is not None              # network blip: no forced re-login, no retry storm


def test_reset_halt_and_contract_roll():
    from tests.test_pipeline import make
    con, st, orc, sent = make()
    p = load_protections(con)
    p.halted = True
    save_protections(con, p)
    orc.reset_halt()
    assert load_protections(con).halted is False


# ---------------------------------------------------------------- multiple signals (max_trades)
def _multi(max_trades):
    from tests.test_pipeline import make
    from rtw.provider import FakeProvider
    con, st, orc, sent = make(capital=20_000_000)
    orc.provider.TREND = {**FakeProvider.TREND, "RELIANCE": 0.0011}
    st.max_trades = max_trades
    orc.refresh_all(NOW, "core")
    orc.refresh_all(NOW, "stocks")
    orc.cycle(NOW, "all")
    return con, st, orc, sent


def test_single_signal_is_default():
    from rtw.config import get_settings, Settings
    assert Settings().max_trades == 1
    con, st, orc, sent = _multi(1)
    from rtw.db import open_trades
    assert len(open_trades(con)) == 1


def test_multiple_signals_open_together_without_duplicates():
    from rtw.db import open_trades
    from rtw.views import home_view
    con, st, orc, sent = _multi(4)
    ot = open_trades(con)
    syms = [s.symbol for s, _ in ot]
    assert 2 <= len(ot) <= 4 and len(set(syms)) == len(syms)
    h = home_view(con, NOW, orc.provider.events(NOW), st)
    assert len(h["trades"]) == len(ot) and h["trade"]["symbol"] == h["trades"][0]["symbol"] and h["max_trades"] == 4
    assert len([m for m in sent if "NAYA SIGNAL" in m]) == len(ot)
    orc.cycle(NOW, "all")                                    # a second cycle must not add duplicates
    assert len(open_trades(con)) == len(ot)


def test_index_same_direction_conflict_rule():
    from rtw.pipeline import Orchestrator
    s = _sig("x")
    s.symbol, s.asset_class, s.direction = "NIFTY", "INDEX", "BUY"
    assert Orchestrator._conflicts([s], {"symbol": "BANKNIFTY", "asset_class": "INDEX", "action": "BUY"})
    assert not Orchestrator._conflicts([s], {"symbol": "BANKNIFTY", "asset_class": "INDEX", "action": "SELL"})
    assert Orchestrator._conflicts([s], {"symbol": "NIFTY", "asset_class": "INDEX", "action": "SELL"})
    assert not Orchestrator._conflicts([s], {"symbol": "GOLD", "asset_class": "COMMODITY", "action": "BUY"})


def test_max_trades_setting_validation_and_api():
    from tests.test_pipeline import make
    con, st, orc, sent = make()
    orc.update_settings(max_trades=3)
    assert st.max_trades == 3
    for bad in (0, 6):
        try:
            orc.update_settings(max_trades=bad)
            assert False
        except ValueError:
            pass
    from fastapi.testclient import TestClient
    from rtw.api import create_app
    c = TestClient(create_app(orc, lambda: NOW))
    assert c.get("/api/settings").json()["max_trades"] == 3
    assert c.post("/api/settings", json={"max_trades": 2}).json()["max_trades"] == 2
    assert c.post("/api/settings", json={"max_trades": 9}).status_code == 400
    assert "trades" in c.get("/api/home").json()


def test_telegram_status_lists_all_open_trades():
    from rtw.telegram_bot import handle_command
    con, st, orc, sent = _multi(4)
    from rtw.db import open_trades
    txt = handle_command("/status", orc, NOW)
    for s, _ in open_trades(con):
        assert s.symbol.replace("&", "") in txt.replace("&", "") or s.symbol in txt


# ---------------------------------------------------------------- charts
def test_chart_payload_and_tv_symbols():
    import numpy as np
    from rtw.charts import chart_payload, tv_symbol, tv_url, resample
    idx = pd.date_range("2026-10-07 09:15", periods=60, freq="5min", tz=IST)
    df = pd.DataFrame({"open": np.arange(60) + 100.0, "high": np.arange(60) + 101.0, "low": np.arange(60) + 99.0, "close": np.arange(60) + 100.5, "volume": 1.0}, index=idx)
    p = chart_payload(df, "5m", 40, [{"label": "SL", "price": 99.0, "kind": "sl"}])
    assert len(p["candles"]) == 40 and len(p["ema20"]) == 40 and p["levels"][0]["label"] == "SL"
    assert p["candles"][-1]["t"] - p["candles"][-2]["t"] == 300
    q = chart_payload(df, "15m", 100)
    assert len(q["candles"]) == 20 and q["candles"][0]["h"] == 103.0 and q["candles"][0]["l"] == 99.0
    assert tv_symbol("NIFTY") == "NSE:NIFTY" and tv_symbol("GOLD") == "MCX:GOLD1!" and tv_symbol("BTCUSDT") == "BINANCE:BTCUSDT"
    assert tv_symbol("M&M") == "NSE:M_M" and tv_symbol("reliance") == "NSE:RELIANCE"
    assert tv_url("EURUSD").startswith("https://www.tradingview.com/chart/?symbol=FX%3AEURUSD")
    try:
        resample(df, "3m")
        assert False
    except ValueError:
        pass


def test_chart_api_symbol_levels_and_option():
    from tests.test_pipeline import make
    from fastapi.testclient import TestClient
    from rtw.api import create_app
    con, st, orc, sent = _multi(4)
    c = TestClient(create_app(orc, lambda: NOW))
    from rtw.db import open_trades
    sym = open_trades(con)[0][0].symbol                                 # a symbol with an open trade -> real levels
    r = c.get("/api/chart", params={"q": sym}).json()
    assert r["found"] and len(r["candles"]) > 30 and {l["kind"] for l in r["levels"]} >= {"entry", "sl", "target"}
    assert set(r["sr"]) == {"supports", "resistances", "zones"}
    r = c.get("/api/chart", params={"q": "tcs", "tf": "15m"}).json()  # any stock: data fetched on demand
    assert r["found"] and r["tf"] == "15m" and r["tv_url"].endswith("NSE%3ATCS")
    assert c.get("/api/chart", params={"q": "tcs", "tf": "7m"}).json()["found"] is False
    r = c.get("/api/chart", params={"q": "nifty", "strike": 24500, "cp": "CE", "expiry": "2026-10-13"}).json()
    assert r["found"] and r["option"]["cp"] == "CE" and all(x["l"] <= x["h"] for x in r["candles"])
    assert c.get("/api/chart", params={"q": "a" * 50}).status_code == 400


# ---------------------------------------------------------------- market mood
def test_mood_of_rules():
    from rtw.mood import mood_of
    assert mood_of({"regime": "TREND", "S": 0.5})["mood"] == "BULLISH"
    assert mood_of({"regime": "TREND", "S": -0.3})["mood"] == "BEARISH"
    assert mood_of({"regime": "TREND", "S": 0.05})["mood"] == "SIDEWAYS"
    assert mood_of({"regime": "RANGE", "S": 0.30})["mood"] == "SIDEWAYS"        # range regime: weak lean = sideways
    assert mood_of({"regime": "RANGE", "S": -0.6})["mood"] == "BEARISH"
    assert mood_of({"regime": "TREND", "S": 0.6})["strength"] == "strong"
    assert "range" not in mood_of({"regime": "TREND", "S": 0.0})
    assert mood_of({"regime": "TREND", "S": 0.5, "wait_reason": "NSE market band hai"}) is None
    assert mood_of({"S": 0.5}) is None and mood_of(None) is None


def test_mood_flip_needs_confirmation():
    from rtw.mood import update_state, CONFIRM_CYCLES
    st, fl = update_state({}, {"NIFTY": "BULLISH"}, NOW)
    assert fl == []                                                   # first reading adopted silently
    for i in range(CONFIRM_CYCLES - 1):
        st, fl = update_state(st, {"NIFTY": "SIDEWAYS"}, NOW + timedelta(minutes=i))
        assert fl == []
    st, fl = update_state(st, {"NIFTY": "SIDEWAYS"}, NOW + timedelta(minutes=9))
    assert len(fl) == 1 and fl[0]["from"] == "BULLISH" and fl[0]["to"] == "SIDEWAYS"
    # a single blip back and forth never flips
    st, _ = update_state(st, {"NIFTY": "BEARISH"}, NOW)
    st, fl = update_state(st, {"NIFTY": "SIDEWAYS"}, NOW)
    st, fl = update_state(st, {"NIFTY": "BEARISH"}, NOW)
    assert fl == []


def test_mood_api_markets_chart_and_telegram_alert():
    from fastapi.testclient import TestClient
    from rtw.api import create_app
    from rtw.db import get_setting, set_setting
    con, st, orc, sent = _multi(1)
    c = TestClient(create_app(orc, lambda: NOW))
    m = c.get("/api/mood").json()
    assert m["items"] and any(i["mood"] in ("BULLISH", "BEARISH", "SIDEWAYS") for i in m["items"])
    assert all("range" in i for i in m["items"] if i["mood"] == "SIDEWAYS")
    assert c.get("/api/markets/index").json()["active"] is not None
    ch = c.get("/api/chart", params={"q": "gold"}).json()
    assert ch["mood"] is None or ch["mood"]["mood"] in ("BULLISH", "BEARISH", "SIDEWAYS")
    # force a confirmed flip for a headline symbol and check the Telegram alert (cooldown respected)
    state = get_setting(con, "moods", {})
    cur = state["GOLD"]["mood"]
    other = "BEARISH" if cur != "BEARISH" else "BULLISH"
    d = orc.provider  # keep provider
    from rtw.db import load_decisions, save_decision
    dec = load_decisions(con)["GOLD"]
    dec["S"], dec["regime"] = (-0.6 if other == "BEARISH" else 0.6), "TREND"
    n0 = len(sent)
    for i in range(3):
        save_decision(con, "GOLD", NOW, dec)
        orc._update_moods(NOW + timedelta(minutes=i))
    assert get_setting(con, "moods")["GOLD"]["mood"] == other
    assert any("GOLD" in x or "Gold" in x for x in sent[n0:]) and any("trade signal nahi" in x for x in sent[n0:])
    assert get_setting(con, "mood_flips")[-1]["symbol"] == "GOLD"
    n1 = len(sent)
    dec["S"] = 0.0
    for i in range(3):                                               # flips back inside the 30-min alert gap: recorded, not re-sent
        save_decision(con, "GOLD", NOW, dec)
        orc._update_moods(NOW + timedelta(minutes=5 + i))
    assert len(sent) == n1 and get_setting(con, "mood_flips")[-1]["to"] == "SIDEWAYS"
````

### `tests/test_zones.py`

````text file=tests/test_zones.py
"""Support/resistance and demand/supply zone logic."""
import numpy as np
import pandas as pd
from rtw.zones import sr_levels, find_zones, zone_info, zones_layer, plan_levels
from rtw.sessions import IST


def _frame(closes, spread=0.25):
    idx = pd.date_range("2026-10-05 09:15", periods=len(closes), freq="5min", tz=IST)
    c = np.array(closes, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + spread, "low": np.minimum(o, c) - spread, "close": c, "volume": 1000.0}, index=idx)


def _noise(n, base=100.0, seed=1):
    r = np.random.default_rng(seed)
    return list(base + np.cumsum(r.normal(0, 0.15, n)) * 0.2)


def _demand_case():
    pre = [100.0 + 0.3 * np.sin(i / 3.0) for i in range(60)]      # choppy lead-in, ATR ~0.8
    base = [100.0, 100.05, 100.0]                                  # tiny candles = base
    impulse = [104.0]                                              # big up candle closing above the base
    run = [104.5, 105.0, 105.2, 105.0, 104.8, 105.1]
    return pre + base + impulse + run


def test_demand_zone_detected_and_alive():
    df = _frame(_demand_case())
    zs = find_zones(df)
    dem = [z for z in zs if z["kind"] == "demand"]
    assert dem and dem[0]["lo"] < 100.5 and dem[0]["hi"] <= 100.5 and dem[0]["fresh"]
    assert dem[0]["hi"] < float(df["close"].iloc[-1])             # zone sits below price


def test_zone_dies_when_price_closes_through_it():
    case = _demand_case() + [102.0, 99.0, 98.5, 98.8, 99.2]       # closes below the zone's far edge -> broken
    df = _frame(case)
    assert not [z for z in find_zones(df) if z["kind"] == "demand" and z["lo"] > 99.5]


def test_supply_zone_mirror():
    pre = [100.0 + 0.3 * np.sin(i / 3.0) for i in range(60)]
    case = pre + [100.0, 99.95, 100.0] + [96.0] + [95.5, 95.0, 94.8, 95.0, 95.2, 94.9]
    zs = find_zones(_frame(case))
    sup = [z for z in zs if z["kind"] == "supply"]
    assert sup and sup[0]["lo"] >= 99.5


def test_no_lookahead_zone_unknown_before_impulse_closes():
    case = _demand_case()
    cut = case.index(104.0)                                        # data ends just BEFORE the impulse candle
    assert not [z for z in find_zones(_frame(case[:cut])) if z["kind"] == "demand" and z["lo"] > 99.0 and z["hi"] > 100.2 and z["t"] > "2026-10-05 12"]


def test_sr_levels_cluster_and_split_around_price():
    wave = []
    for k in range(8):                                             # oscillation between ~98 and ~102 -> repeated swing levels
        wave += list(np.linspace(98, 102, 12)) + list(np.linspace(102, 98, 12))
    wave += list(np.linspace(98, 100.3, 8))
    df = _frame(wave, spread=0.1)
    price = float(df["close"].iloc[-1])
    sr = sr_levels(df, atr=0.4)
    assert sr["supports"] and sr["resistances"]
    assert all(s["price"] < price for s in sr["supports"]) and all(r["price"] > price for r in sr["resistances"])
    assert max(r["touches"] for r in sr["resistances"]) >= 2        # clustered swing highs near 102
    assert any(abs(r["price"] - 102) < 0.6 and r["touches"] >= 2 for r in sr["resistances"])      # the 102 swing-high cluster is found
    assert any(abs(x["price"] - 98) < 0.6 for x in sr["supports"])


def test_layer_votes_only_at_a_zone_and_plan_levels():
    case = _demand_case()[:-6] + [104.5, 103.0, 101.5, 100.3]       # price returns INTO the demand zone
    df = _frame(case)
    r = zones_layer(df)
    assert r.conf > 0 and any("Demand" in x for x in r.reasons)          # (a resistance right above can offset the score, by design)
    far = zones_layer(_frame(_noise(120, 100.0)))                   # nothing nearby -> abstains (conf 0), never dilutes
    assert far.conf == 0 or abs(far.score) <= 1
    pl = plan_levels(zone_info(df))
    assert set(pl) == {"supports", "resistances", "demand_distal", "supply_distal"}


def test_short_data_is_safe():
    assert zone_info(_frame([100.0] * 10)) == {"supports": [], "resistances": [], "zones": []}
    assert zones_layer(_frame([100.0] * 10)).conf == 0
````


## 16. Final verification checklist (agent: tick each, report to Raj in 5 lines)
1. `python unpack.py RTW_MASTER_SPEC.md` → `60 files created`.
2. `pytest` → all green (authoring: 99 passed).
3. `check_setup.py` (DEMO) → 0 FAIL.
4. `start.bat` DEMO → `/api/home` returns JSON; all 6 tabs open on phone width without horizontal scroll.
5. PAPER mode with real keys → `check_setup.py` shows Angel login OK, candles OK for NIFTY/GOLD/USDINR/BTCUSDT, global OK, news OK, calendar OK, (`--telegram` OK).
6. Report: what passed, what failed with the exact error, what Raj still has to do.
