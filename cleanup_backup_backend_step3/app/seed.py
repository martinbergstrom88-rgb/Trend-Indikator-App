"""Initial data for a completely new Trading Indicator database.

Default tickers are inserted only when the ticker table is empty. This keeps
products intentionally removed by the user from being recreated on restart.
"""

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
    """Seed defaults once, while preserving all later user changes."""
    database_has_tickers = session.exec(select(Ticker.symbol).limit(1)).first() is not None

    if not database_has_tickers:
        session.add_all(
            [
                Ticker(
                    symbol=symbol,
                    name=name,
                    asset_type=asset_type,
                    currency=currency,
                    tradingview_symbol=tradingview_symbol,
                    is_favorite=symbol == "BTC-USD",
                )
                for symbol, name, asset_type, currency, tradingview_symbol in DEFAULTS
            ]
        )

    if session.get(AppSetting, "signal_alerts_enabled") is None:
        session.add(AppSetting(key="signal_alerts_enabled", value="true"))

    session.commit()
