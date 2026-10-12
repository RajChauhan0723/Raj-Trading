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
        from .sessions import is_open
        if spec.has_options and (self.demo or is_open(spec.segment, now, self.provider.holidays())):
            chain = self.provider.option_chain(spec, now)
            if chain:
                extra["options"] = options_layer(chain.get("spot") or float(df["close"].iloc[-1]), chain["rows"], chain.get("iv_pct"))
        lot, cap = self._engine_lot_and_capital(spec, ctx)
        want_option = bool(chain or spec.has_options or spec.asset_class == "INDEX")
        age = data_age_sec(df, now)
        ok_prot, why_prot = prot.can_trade(now)

        def run(paper: bool, exp, ntr):
            return analyze(spec.symbol, spec.asset_class, df, now, capital=cap, risk_pct=self.st.risk_pct, lot_size=lot,
                           profile=self.st.profile, segment=seg, intraday=True, extra_layers=extra, tags=ctx["tags"], events=ctx["events"],
                           data_age_sec=age, setup_expectancy=exp, setup_trades=ntr, paper=paper, daily_loss_hit=prot.daily_loss_hit(now),
                           protections_ok=(ok_prot, why_prot), vix_z=(ctx["vix_z"] if spec.segment == "NSE" else None), holidays=self.provider.holidays(),
                           skip_afford=(want_option or spec.asset_class == "INDEX" or paper))

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
            if spec.symbol == "XAUUSD":
                d["extra"].update(lots=pl["lots"], risk_amount=pl["risk_amount"], currency="USD",
                                  plan_note="International Spot Gold ($/oz) benchmark")
                d["instrument"] = "XAUUSD (Spot Gold)"
                return d
            contract_key = spec.symbol if spec.symbol in MCX_CONTRACTS else spec.group
            c = choose_contract(contract_key, pl["sl_dist"], d["risk_budget"])
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
        if spec.has_options and not chain:
            spot = d.get("price") or (pl["entry_lo"] + pl["entry_hi"]) / 2
            step = 50 if spec.symbol == "NIFTY" else 100 if spec.symbol in ("BANKNIFTY", "SENSEX") else 25 if spec.symbol == "MIDCPNIFTY" else max(1.0, round(spot * 0.01))
            strike = round(spot / step) * step
            cp = "CE" if d["action"] == "BUY" else "PE"
            delta = 0.50
            atr_v = d.get("atr") or max(10.0, pl["sl_dist"] / 1.5)
            approx_prem = max(20.0, round(1.3 * atr_v, 1))
            sl_prem = max(2.0, round(approx_prem - delta * pl["sl_dist"], 1))
            t1_prem = round(approx_prem + delta * abs(pl["t1"] - spot), 1)
            t2_prem = round(approx_prem + delta * abs(pl["t2"] - spot), 1)
            lot = spec.lot or 50
            lots = max(1, pl.get("lots") or 1)
            pl["lots"] = lots
            pl["affordable"] = True
            opt = {
                "cp": cp, "strike": strike, "expiry": "Current Expiry", "dte": 3.0,
                "premium": approx_prem, "sl_prem": sl_prem, "sl_premium": sl_prem,
                "t1_premium": t1_prem, "t2_premium": t2_prem,
                "pop": 0.60, "breakeven": strike + approx_prem if cp == "CE" else strike - approx_prem,
                "expected_move": atr_v * 2.0, "iv": 0.14, "delta": delta, "synthetic": True
            }
            d["extra"].update(
                option=opt, lots=lots, lot_size=lot,
                max_loss=approx_prem * lot * lots,
                risk_amount=(approx_prem - sl_prem) * lot * lots
            )
            d["instrument"] = f"{spec.symbol} {strike:g} {cp}"
            return d
        if pl.get("lots", 0) == 0:
            pl["lots"] = 1
            pl["affordable"] = True
            pl["risk_amount"] = pl["sl_dist"] * (spec.lot or 1)
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
                c_row = self.con.execute("SELECT close FROM candles WHERE symbol=? ORDER BY ts DESC LIMIT 1", (sp.symbol,)).fetchone()
                last_price = c_row[0] if (c_row and c_row[0] is not None) else None
                save_decision(self.con, sp.symbol, now, {"symbol": sp.symbol, "name": sp.name, "price": last_price, "action": "WAIT", "wait_reason": f"{sp.segment} market band hai", "S": 0.0, "A": 0.0})
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
        cached = load_decisions(self.con).get(sp.symbol)
        if cached:
            cached = dict(cached)
            if not cached.get("price"):
                c_row = self.con.execute("SELECT close FROM candles WHERE symbol=? ORDER BY ts DESC LIMIT 1", (sp.symbol,)).fetchone()
                if c_row and c_row[0] is not None:
                    cached["price"] = c_row[0]
            cached["info_only"] = True
            return {"found": True, "symbol": sp.symbol, "name": sp.name, "decision": cached}
        df = load_df(self.con, sp.symbol, "5m", 60)
        has_data = df is not None and len(df) >= 30
        if not has_data:
            if not self.refresh_symbol(sp, now):
                return {"found": False, "symbol": sp.symbol, "message": f"{sp.symbol} ka data nahi mila"}
        d = self.analyze_spec(sp, now, self.context(now), get_setup_stats(self.con), load_protections(self.con))
        d["info_only"] = True
        return {"found": True, "symbol": sp.symbol, "name": sp.name, "decision": d}

    def chart(self, q: str, now: datetime, tf: str = "5m", strike: float | None = None, cp: str | None = None, expiry: str | None = None) -> dict:
        """Chart of any symbol (or of one option contract when strike/cp/expiry are given). Levels come from the open trade, else
        from the current BUY/SELL plan (marked INFO). Candles are closed bars only."""
        from .charts import chart_payload, levels_from_plan, tv_url, TFS
        if tf == "1m":
            tf = "5m"
        elif tf not in TFS:
            return {"found": False, "message": "tf 1m / 5m / 15m / 1h me se ek ho"}
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
