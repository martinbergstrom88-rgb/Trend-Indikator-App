"""Convert instrument currencies to SEK, cached for one hour."""
import threading, time
import pandas as pd
import yfinance as yf
_cache: dict[str, tuple[float,float]] = {}
_lock=threading.Lock(); _download_lock=threading.Lock()

def rate_to_sek(currency: str | None, force: bool=False) -> float:
    code=(currency or "SEK").upper()
    if code in {"SEK","KR"}: return 1.0
    now=time.time()
    with _lock:
        saved=_cache.get(code)
        if saved and not force and now-saved[0] < 3600: return saved[1]
    with _download_lock:
        frame=yf.download(f"{code}SEK=X",period="5d",interval="1d",auto_adjust=True,repair=False,progress=False,threads=False,timeout=15,multi_level_index=False)
    if frame is None or frame.empty: raise ValueError(f"Ingen valutakurs för {code}/SEK")
    close=frame["Close"]
    if isinstance(close,pd.DataFrame): close=close.iloc[:,0]
    rate=float(close.dropna().iloc[-1])
    with _lock: _cache[code]=(now,rate)
    return rate
