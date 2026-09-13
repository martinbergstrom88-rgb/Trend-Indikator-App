from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, delete
from .config import get_settings
from .database import create_db_and_tables, engine, get_session
from .migrations import migrate_database
from .market import snapshot_dict
from .currency import rate_to_sek
from .models import (AlertCreate, AppSetting, Holding, HoldingUpsert, PriceAlert,
                     SignalHistory, Ticker, TickerCreate, TickerPatch, DeviceToken, DeviceTokenCreate, SignalAlert, SignalAlertUpdate, PriceAlertUpdate)
from .seed import seed
from .notifications import firebase_ready, start_worker, stop_worker, check_alerts
from .routers import health, market

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    migrate_database()
    with Session(engine) as session:
        seed(session)
    start_worker()
    yield
    stop_worker()

app = FastAPI(title="Trend Indikator API", version="5.2.4", lifespan=lifespan)
app.include_router(health.router)
app.include_router(market.router)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origin_list,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

from .services.market_payload import market_payload

@app.get("/api/v1/tickers/{symbol}")
def ticker_detail(symbol: str, refresh: bool = False, session: Session = Depends(get_session)):
    row = session.get(Ticker, symbol.upper())
    if not row: raise HTTPException(404, "Tickern finns inte")
    history = session.exec(select(SignalHistory).where(SignalHistory.ticker_symbol == row.symbol).order_by(SignalHistory.changed_at.desc())).all()
    holding = session.exec(select(Holding).where(Holding.ticker_symbol == row.symbol)).first()
    return {**market_payload(row, refresh, session), "signal_history": history,
            "holding": holding.model_dump() if holding else None,
            "tradingview_url": f"https://www.tradingview.com/chart/?symbol={row.tradingview_symbol}" if row.tradingview_symbol else None}

@app.post("/api/v1/tickers", response_model=Ticker, status_code=201)
def add_ticker(data: TickerCreate, session: Session = Depends(get_session)):
    symbol = data.symbol.upper().strip()
    if session.get(Ticker, symbol): raise HTTPException(409, "Tickern finns redan")
    row = Ticker(**data.model_dump(exclude={"symbol"}), symbol=symbol)
    session.add(row); session.commit(); session.refresh(row); return row

@app.patch("/api/v1/tickers/{symbol}", response_model=Ticker)
def patch_ticker(symbol: str, data: TickerPatch, session: Session = Depends(get_session)):
    row = session.get(Ticker, symbol.upper())
    if not row: raise HTTPException(404, "Tickern finns inte")
    for key, value in data.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    session.add(row); session.commit(); session.refresh(row); return row

@app.delete("/api/v1/tickers/{symbol}", status_code=204)
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

@app.get("/api/v1/holdings")
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

@app.put("/api/v1/holdings/{symbol}", response_model=Holding)
def upsert_holding(symbol: str, data: HoldingUpsert, session: Session = Depends(get_session)):
    symbol = symbol.upper()
    if not session.get(Ticker, symbol): raise HTTPException(404, "Lägg först till tickern i marknadslistan")
    row = session.exec(select(Holding).where(Holding.ticker_symbol == symbol)).first()
    if row:
        for k,v in data.model_dump().items(): setattr(row,k,v)
    else: row = Holding(ticker_symbol=symbol, **data.model_dump())
    session.add(row); session.commit(); session.refresh(row); return row

@app.delete("/api/v1/holdings/{symbol}", status_code=204)
def delete_holding(symbol: str, session: Session = Depends(get_session)):
    row = session.exec(select(Holding).where(Holding.ticker_symbol == symbol.upper())).first()
    if not row: raise HTTPException(404, "Innehavet finns inte")
    session.delete(row); session.commit()

@app.get("/api/v1/alerts")
def get_alerts(session: Session = Depends(get_session)):
    enabled = session.get(AppSetting, "signal_alerts_enabled")
    return {"signal_alerts_enabled": enabled.value == "true" if enabled else True,
            "price_alerts": session.exec(select(PriceAlert)).all()}

@app.put("/api/v1/alerts/signal")
def signal_alert(enabled: bool = Query(...), session: Session = Depends(get_session)):
    row = session.get(AppSetting, "signal_alerts_enabled") or AppSetting(key="signal_alerts_enabled", value="true")
    row.value = str(enabled).lower(); session.add(row); session.commit(); return {"enabled": enabled}

@app.post("/api/v1/alerts/price", response_model=PriceAlert, status_code=201)
def add_alert(data: AlertCreate, session: Session = Depends(get_session)):
    symbol, direction = data.ticker_symbol.upper(), data.direction.strip()
    if direction not in (">", "<"): raise HTTPException(422, "direction måste vara > eller <")
    if not session.get(Ticker, symbol): raise HTTPException(404, "Tickern finns inte")
    row = PriceAlert(**data.model_dump(exclude={"ticker_symbol", "direction"}), ticker_symbol=symbol, direction=direction, triggered=False, last_condition_met=None)
    session.add(row); session.commit(); session.refresh(row); return row

@app.delete("/api/v1/alerts/price/{alert_id}", status_code=204)
def delete_alert(alert_id: int, session: Session = Depends(get_session)):
    row = session.get(PriceAlert, alert_id)
    if not row: raise HTTPException(404, "Larmet finns inte")
    session.delete(row); session.commit()


@app.post("/api/v1/devices", status_code=201)
def register_device(data: DeviceTokenCreate, session: Session = Depends(get_session)):
    row=session.exec(select(DeviceToken).where(DeviceToken.token==data.token)).first()
    if row: row.enabled=True;row.platform=data.platform
    else: row=DeviceToken(token=data.token,platform=data.platform)
    session.add(row);session.commit();session.refresh(row);return row

@app.get("/api/v1/notifications/status")
def notification_status(): return {"firebase_ready":firebase_ready()}

@app.get("/api/v1/tickers/{symbol}/notifications")
def product_notifications(symbol: str, session: Session = Depends(get_session)):
    symbol=symbol.upper();signal=session.exec(select(SignalAlert).where(SignalAlert.ticker_symbol==symbol)).first();prices=session.exec(select(PriceAlert).where(PriceAlert.ticker_symbol==symbol)).all()
    return {"signal_enabled":signal.enabled if signal else False,"price_alerts":prices}

@app.put("/api/v1/tickers/{symbol}/notifications/signal")
def update_signal_notification(symbol: str,data: SignalAlertUpdate,session: Session=Depends(get_session)):
    symbol=symbol.upper()
    if not session.get(Ticker,symbol):raise HTTPException(404,"Tickern finns inte")
    row=session.exec(select(SignalAlert).where(SignalAlert.ticker_symbol==symbol)).first()
    if row:row.enabled=data.enabled
    else:row=SignalAlert(ticker_symbol=symbol,enabled=data.enabled)
    session.add(row);session.commit();session.refresh(row);return row

@app.post("/api/v1/tickers/{symbol}/notifications/price",status_code=201)
def product_price_notification(symbol:str,data:AlertCreate,session:Session=Depends(get_session)):
    symbol=symbol.upper();direction=data.direction.strip()
    if direction not in (">","<"):raise HTTPException(422,"direction måste vara > eller <")
    row=PriceAlert(ticker_symbol=symbol,direction=direction,target_price=data.target_price,enabled=data.enabled,triggered=False,last_condition_met=None);session.add(row);session.commit();session.refresh(row);return row

@app.patch("/api/v1/notifications/price/{alert_id}")
def patch_price_notification(alert_id:int,data:PriceAlertUpdate,session:Session=Depends(get_session)):
    row=session.get(PriceAlert,alert_id)
    if not row:raise HTTPException(404,"Larmet finns inte")
    row.enabled=data.enabled;session.add(row);session.commit();session.refresh(row);return row

@app.delete("/api/v1/notifications/price/{alert_id}",status_code=204)
def remove_price_notification(alert_id:int,session:Session=Depends(get_session)):
    row=session.get(PriceAlert,alert_id)
    if not row:raise HTTPException(404,"Larmet finns inte")
    session.delete(row);session.commit()

@app.get("/api/v1/notifications/active")
def active_notifications(session:Session=Depends(get_session)):
    signals=session.exec(select(SignalAlert).where(SignalAlert.enabled==True)).all();prices=session.exec(select(PriceAlert).where(PriceAlert.enabled==True)).all()
    def ticker_data(symbol):
        row=session.get(Ticker,symbol);return row.model_dump() if row else {"symbol":symbol,"name":symbol}
    return {"firebase_ready":firebase_ready(),"signal_alerts":[{"alert":x.model_dump(),"ticker":ticker_data(x.ticker_symbol)} for x in signals],"price_alerts":[{"alert":x.model_dump(),"ticker":ticker_data(x.ticker_symbol)} for x in prices]}

@app.post("/api/v1/notifications/check")
def check_notifications_now():check_alerts();return {"ok":True}
