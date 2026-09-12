from dataclasses import dataclass
from datetime import date
import pandas as pd

SIGNAL_YELLOW = "yellow"
SIGNAL_GRAY = "gray"
SIGNAL_NAVY = "navy"

@dataclass(frozen=True)
class IndicatorResult:
    signal: str
    signal_since: date | None
    previous_signal: str | None

def smma(series: pd.Series, length: int) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").astype(float)
    out = pd.Series(index=s.index, dtype="float64")
    first = s.first_valid_index()
    if first is None:
        return out
    start = s.index.get_loc(first)
    if start + length > len(s):
        return out
    seed_pos = start + length - 1
    out.iloc[seed_pos] = s.iloc[start:start + length].mean()
    for i in range(seed_pos + 1, len(s)):
        if pd.isna(s.iloc[i]):
            out.iloc[i] = out.iloc[i - 1]
        else:
            out.iloc[i] = (out.iloc[i - 1] * (length - 1) + s.iloc[i]) / length
    return out

def signal_series(high: pd.Series, low: pd.Series) -> pd.Series:
    hl2 = (high.astype(float) + low.astype(float)) / 2
    v1, m1, m2, v2 = (smma(hl2, n) for n in (15, 19, 25, 29))
    result = pd.Series(index=hl2.index, dtype="object")
    valid = v1.notna() & m1.notna() & m2.notna() & v2.notna()
    p2 = ((v1 < m1) != (v1 < v2)) | ((m2 < v2) != (v1 < v2))
    p3 = (~p2) & (v1 < v2)
    result.loc[valid & ~p2 & ~p3] = SIGNAL_YELLOW
    result.loc[valid & p2] = SIGNAL_GRAY
    result.loc[valid & p3] = SIGNAL_NAVY
    return result

def current_indicator(high: pd.Series, low: pd.Series) -> IndicatorResult:
    signals = signal_series(high, low).dropna()
    if signals.empty:
        raise ValueError("För lite historik för indikatorn")
    current = str(signals.iloc[-1])
    change_positions = [i for i in range(1, len(signals)) if signals.iloc[i] != signals.iloc[i - 1]]
    if not change_positions:
        return IndicatorResult(current, None, None)
    pos = change_positions[-1]
    when = pd.Timestamp(signals.index[pos]).date()
    return IndicatorResult(current, when, str(signals.iloc[pos - 1]))

def percent_change(close: pd.Series, days: int) -> float | None:
    close = pd.to_numeric(close, errors="coerce").dropna()
    if close.empty:
        return None
    target = pd.Timestamp(close.index[-1]) - pd.Timedelta(days=days)
    distances = pd.Series(abs(pd.DatetimeIndex(close.index) - target), index=close.index)
    idx = distances.idxmin()
    if distances.loc[idx] > pd.Timedelta(days=14) or float(close.loc[idx]) <= 0:
        return None
    return round((float(close.iloc[-1]) / float(close.loc[idx]) - 1) * 100, 2)
