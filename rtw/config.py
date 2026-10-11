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
        stocks_top_n=int(_f("RTW_STOCKS_TOP_N", 50)), max_trades=max(1, min(5, int(_f("RTW_MAX_TRADES", 1)))), host=g("RTW_HOST", "0.0.0.0"), port=int(g("PORT") or _f("RTW_PORT", 8000)))


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
