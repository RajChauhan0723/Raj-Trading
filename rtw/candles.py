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
