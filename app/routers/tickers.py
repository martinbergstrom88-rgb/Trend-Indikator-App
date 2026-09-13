from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Holding,
    PriceAlert,
    SignalHistory,
    Ticker,
    TickerCreate,
    TickerPatch,
)
from ..services.market_payload import market_payload

router = APIRouter()


@router.get("/api/v1/tickers/{symbol}")
def ticker_detail(symbol: str, refresh: bool = False, session: Session = Depends(get_session)):
    row = session.get(Ticker, symbol.upper())
    if not row: raise HTTPException(404, "Tickern finns inte")
    history = session.exec(select(SignalHistory).where(SignalHistory.ticker_symbol == row.symbol).order_by(SignalHistory.changed_at.desc())).all()
    holding = session.exec(select(Holding).where(Holding.ticker_symbol == row.symbol)).first()
    return {**market_payload(row, refresh, session), "signal_history": history,
            "holding": holding.model_dump() if holding else None,
            "tradingview_url": f"https://www.tradingview.com/chart/?symbol={row.tradingview_symbol}" if row.tradingview_symbol else None}

@router.post("/api/v1/tickers", response_model=Ticker, status_code=201)
def add_ticker(data: TickerCreate, session: Session = Depends(get_session)):
    symbol = data.symbol.upper().strip()
    if session.get(Ticker, symbol): raise HTTPException(409, "Tickern finns redan")
    row = Ticker(**data.model_dump(exclude={"symbol"}), symbol=symbol)
    session.add(row); session.commit(); session.refresh(row); return row

@router.patch("/api/v1/tickers/{symbol}", response_model=Ticker)
def patch_ticker(symbol: str, data: TickerPatch, session: Session = Depends(get_session)):
    row = session.get(Ticker, symbol.upper())
    if not row: raise HTTPException(404, "Tickern finns inte")
    for key, value in data.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    session.add(row); session.commit(); session.refresh(row); return row

@router.delete("/api/v1/tickers/{symbol}", status_code=204)
def delete_ticker(symbol: str, session: Session = Depends(get_session)):
    symbol = symbol.upper()
    row = session.get(Ticker, symbol)
    if not row:
        raise HTTPException(404, "Tickern finns inte")
    holding = session.exec(select(Holding).where(Holding.ticker_symbol == symbol)).first()
    if holding:
        session.delete(holding)
    for alert in session.exec(select(PriceAlert).where(PriceAlert.ticker_symbol == symbol)).all():
        session.delete(alert)
    for history in session.exec(select(SignalHistory).where(SignalHistory.ticker_symbol == symbol)).all():
        session.delete(history)
    session.delete(row)
    session.commit()
