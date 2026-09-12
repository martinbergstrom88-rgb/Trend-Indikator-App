from sqlmodel import Session, select
from .models import AppSetting, Ticker

DEFAULTS = [
    ("AAPL", "Apple", "stock", "USD", "NASDAQ:AAPL"),
    ("TSLA", "Tesla", "stock", "USD", "NASDAQ:TSLA"),
    ("MSFT", "Microsoft", "stock", "USD", "NASDAQ:MSFT"),
    ("ERIC-B.ST", "Ericsson B", "stock", "SEK", "OMXSTO:ERIC_B"),
    ("HM-B.ST", "H&M B", "stock", "SEK", "OMXSTO:HM_B"),
    ("VOLV-B.ST", "Volvo B", "stock", "SEK", "OMXSTO:VOLV_B"),
    ("INVE-B.ST", "Investor B", "stock", "SEK", "OMXSTO:INVE_B"),
    ("BTC-USD", "Bitcoin", "crypto", "USD", "BITSTAMP:BTCUSD"),
    ("ETH-USD", "Ethereum", "crypto", "USD", "BITSTAMP:ETHUSD"),
    ("SOL-USD", "Solana", "crypto", "USD", "COINBASE:SOLUSD"),
    ("GC=F", "Guld", "commodity", "USD", "COMEX:GC1!"),
    ("SI=F", "Silver", "commodity", "USD", "COMEX:SI1!"),
    ("CL=F", "WTI-olja", "commodity", "USD", "NYMEX:CL1!"),
    ("BZ=F", "Brentolja", "commodity", "USD", "TVC:UKOIL"),
    ("^OMX", "OMX Stockholm 30", "index", "SEK", "OMXSTO:OMXS30"),
    ("^GSPC", "S&P 500", "index", "USD", "SP:SPX"),
    ("^IXIC", "Nasdaq Composite", "index", "USD", "NASDAQ:IXIC"),
    ("^DJI", "Dow Jones", "index", "USD", "DJ:DJI"),
    ("^GDAXI", "DAX", "index", "EUR", "XETR:DAX"),
    ("^FTSE", "FTSE 100", "index", "GBP", "FTSE:UKX"),
]

def seed(session: Session) -> None:
    for symbol, name, asset_type, currency, tv in DEFAULTS:
        if session.get(Ticker, symbol) is None:
            session.add(Ticker(symbol=symbol, name=name, asset_type=asset_type, currency=currency, tradingview_symbol=tv, is_favorite=symbol == "BTC-USD"))
    if session.get(AppSetting, "signal_alerts_enabled") is None:
        session.add(AppSetting(key="signal_alerts_enabled", value="true"))
    session.commit()
