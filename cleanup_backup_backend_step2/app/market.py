from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import threading
import pandas as pd
import yfinance as yf
from .config import get_settings
from .indicator import current_indicator, percent_change

@dataclass
class MarketSnapshot:
    ticker: str
    price: float
    change_today: float | None
    change_3m: float | None
    change_1y: float | None
    change_3y: float | None
    signal: str
    signal_since: str | None
    previous_signal: str | None
    market_time: str | None
    fetched_at: str

_cache: dict[str, tuple[float, MarketSnapshot]] = {}
_lock = threading.Lock()
_download_lock = threading.Lock()

def _series(df: pd.DataFrame, name: str) -> pd.Series:
    value = df[name]
    if isinstance(value, pd.DataFrame):
        value = value.iloc[:, 0]
    return value.squeeze()

def fetch_market_snapshot(ticker: str, force: bool = False) -> MarketSnapshot:
    import time
    ticker = ticker.upper().strip()
    now = time.time()
    ttl = get_settings().cache_ttl_seconds
    with _lock:
        cached = _cache.get(ticker)
        if cached and not force and now - cached[0] < ttl:
            return cached[1]
    with _download_lock:
        df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, repair=False,
                         progress=False, threads=False, timeout=15, multi_level_index=False)
    if df is None or df.empty:
        raise ValueError(f"Ingen marknadsdata hittades för {ticker}")
    high, low, close = (_series(df, x).dropna() for x in ("High", "Low", "Close"))
    common = high.index.intersection(low.index).intersection(close.index)
    high, low, close = high.loc[common], low.loc[common], close.loc[common]
    result = current_indicator(high, low)
    today = None
    if len(close) >= 2 and float(close.iloc[-2]) != 0:
        today = round((float(close.iloc[-1]) / float(close.iloc[-2]) - 1) * 100, 2)
    snap = MarketSnapshot(
        ticker=ticker, price=round(float(close.iloc[-1]), 6), change_today=today,
        change_3m=percent_change(close, 90), change_1y=percent_change(close, 365),
        change_3y=percent_change(close, 1095), signal=result.signal,
        signal_since=result.signal_since.isoformat() if result.signal_since else None,
        previous_signal=result.previous_signal,
        market_time=pd.Timestamp(close.index[-1]).isoformat(),
        fetched_at=datetime.now(timezone.utc).isoformat())
    with _lock:
        _cache[ticker] = (now, snap)
    return snap

def snapshot_dict(ticker: str, force: bool = False) -> dict:
    return asdict(fetch_market_snapshot(ticker, force))
