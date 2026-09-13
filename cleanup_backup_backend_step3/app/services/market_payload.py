from sqlmodel import Session, select

from ..market import snapshot_dict
from ..models import SignalHistory, Ticker


def market_payload(ticker: Ticker, force: bool, session: Session) -> dict:
    try:
        data = snapshot_dict(ticker.symbol, force)
        current = data.get("signal")
        latest = session.exec(
            select(SignalHistory)
            .where(SignalHistory.ticker_symbol == ticker.symbol)
            .order_by(SignalHistory.changed_at.desc())
        ).first()
        if current and (latest is None or latest.new_signal != current):
            session.add(SignalHistory(
                ticker_symbol=ticker.symbol,
                old_signal=latest.new_signal if latest else data.get("previous_signal"),
                new_signal=current,
            ))
            session.commit()
        return {**ticker.model_dump(), **data}
    except Exception as exc:
        return {**ticker.model_dump(), "error": str(exc)}
