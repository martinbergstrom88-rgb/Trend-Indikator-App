import pandas as pd
from app.indicator import signal_series, smma, current_indicator

def test_smma_seed_and_length():
    s = pd.Series(range(1, 41), index=pd.date_range("2024-01-01", periods=40))
    out = smma(s, 15)
    assert out.first_valid_index() == s.index[14]
    assert round(out.iloc[14], 2) == 8.0

def test_signal_is_valid():
    idx = pd.date_range("2024-01-01", periods=120)
    high = pd.Series([100 + i * .2 for i in range(120)], index=idx)
    low = high - 2
    result = current_indicator(high, low)
    assert result.signal in {"yellow", "gray", "navy"}
    assert signal_series(high, low).dropna().shape[0] > 0
