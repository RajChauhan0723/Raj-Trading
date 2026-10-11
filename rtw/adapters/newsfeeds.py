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
