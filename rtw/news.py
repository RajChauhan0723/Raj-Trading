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
