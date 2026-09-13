from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Holding, Ticker
from ..services.market_payload import market_payload

router = APIRouter()


@router.get("/api/v1/catalog")
def catalog(favorite: bool | None = None, asset_type: str | None = None,
            session: Session = Depends(get_session)):
    """Lightweight metadata endpoint. It never downloads market prices."""
    statement = select(Ticker).where(Ticker.is_active == True)
    if favorite is not None:
        statement = statement.where(Ticker.is_favorite == favorite)
    if asset_type:
        statement = statement.where(Ticker.asset_type == asset_type)
    return session.exec(statement).all()

@router.get("/api/v1/holding-records")
def holding_records(session: Session = Depends(get_session)):
    """Return saved holdings immediately, without waiting for Yahoo data."""
    result = []
    for holding in session.exec(select(Holding)).all():
        ticker = session.get(Ticker, holding.ticker_symbol)
        result.append({**holding.model_dump(), "ticker": ticker.model_dump() if ticker else None})
    return result

@router.get("/api/v1/favorites")
def favorites(refresh: bool = False, session: Session = Depends(get_session)):
    rows = session.exec(select(Ticker).where(Ticker.is_favorite == True, Ticker.is_active == True)).all()
    return [market_payload(x, refresh, session) for x in rows]

@router.get("/api/v1/market")
def market(asset_type: str | None = None, q: str | None = None, refresh: bool = False,
           session: Session = Depends(get_session)):
    statement = select(Ticker).where(Ticker.is_active == True)
    if asset_type: statement = statement.where(Ticker.asset_type == asset_type)
    rows = session.exec(statement).all()
    if q: rows = [x for x in rows if q.lower() in f"{x.symbol} {x.name}".lower()]
    return [market_payload(x, refresh, session) for x in rows]
