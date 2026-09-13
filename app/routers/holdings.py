from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..currency import rate_to_sek
from ..database import get_session
from ..market import snapshot_dict
from ..models import Holding, HoldingUpsert, Ticker

router = APIRouter()


@router.get("/api/v1/holdings")
def holdings(refresh: bool = False, session: Session = Depends(get_session)):
    rows = session.exec(select(Holding)).all(); output = []
    for h in rows:
        ticker = session.get(Ticker, h.ticker_symbol)
        item = {**h.model_dump(), "ticker": ticker.model_dump() if ticker else None}
        try:
            snap = snapshot_dict(h.ticker_symbol, refresh)
            currency = ticker.currency if ticker else "SEK"
            fx_rate = rate_to_sek(currency, refresh)
            native_value = snap["price"] * h.quantity
            native_cost = h.purchase_price * h.quantity
            value_sek = native_value * fx_rate
            cost_sek = native_cost * fx_rate
            item.update({"market": snap,
                         "market_value_native": round(native_value, 2),
                         "market_value_sek": round(value_sek, 2),
                         "market_value": round(value_sek, 2),
                         "profit_loss_sek": round(value_sek-cost_sek, 2),
                         "profit_loss": round(value_sek-cost_sek, 2),
                         "fx_rate_to_sek": round(fx_rate, 6),
                         "return_since_purchase": round((native_value/native_cost-1)*100, 2)})
        except Exception as exc: item["error"] = str(exc)
        output.append(item)
    return output

@router.put("/api/v1/holdings/{symbol}", response_model=Holding)
def upsert_holding(symbol: str, data: HoldingUpsert, session: Session = Depends(get_session)):
    symbol = symbol.upper()
    if not session.get(Ticker, symbol): raise HTTPException(404, "Lägg först till tickern i marknadslistan")
    row = session.exec(select(Holding).where(Holding.ticker_symbol == symbol)).first()
    if row:
        for k,v in data.model_dump().items(): setattr(row,k,v)
    else: row = Holding(ticker_symbol=symbol, **data.model_dump())
    session.add(row); session.commit(); session.refresh(row); return row

@router.delete("/api/v1/holdings/{symbol}", status_code=204)
def delete_holding(symbol: str, session: Session = Depends(get_session)):
    row = session.exec(select(Holding).where(Holding.ticker_symbol == symbol.upper())).first()
    if not row: raise HTTPException(404, "Innehavet finns inte")
    session.delete(row); session.commit()
