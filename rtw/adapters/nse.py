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
