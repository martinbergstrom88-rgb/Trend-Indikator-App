from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    AlertCreate,
    AppSetting,
    DeviceToken,
    DeviceTokenCreate,
    PriceAlert,
    PriceAlertUpdate,
    SignalAlert,
    SignalAlertUpdate,
    Ticker,
)
from ..notifications import check_alerts, firebase_ready

router = APIRouter()


@router.get("/api/v1/alerts")
def get_alerts(session: Session = Depends(get_session)):
    enabled = session.get(AppSetting, "signal_alerts_enabled")
    return {"signal_alerts_enabled": enabled.value == "true" if enabled else True,
            "price_alerts": session.exec(select(PriceAlert)).all()}

@router.put("/api/v1/alerts/signal")
def signal_alert(enabled: bool = Query(...), session: Session = Depends(get_session)):
    row = session.get(AppSetting, "signal_alerts_enabled") or AppSetting(key="signal_alerts_enabled", value="true")
    row.value = str(enabled).lower(); session.add(row); session.commit(); return {"enabled": enabled}

@router.post("/api/v1/alerts/price", response_model=PriceAlert, status_code=201)
def add_alert(data: AlertCreate, session: Session = Depends(get_session)):
    symbol, direction = data.ticker_symbol.upper(), data.direction.strip()
    if direction not in (">", "<"): raise HTTPException(422, "direction måste vara > eller <")
    if not session.get(Ticker, symbol): raise HTTPException(404, "Tickern finns inte")
    row = PriceAlert(**data.model_dump(exclude={"ticker_symbol", "direction"}), ticker_symbol=symbol, direction=direction, triggered=False, last_condition_met=None)
    session.add(row); session.commit(); session.refresh(row); return row

@router.delete("/api/v1/alerts/price/{alert_id}", status_code=204)
def delete_alert(alert_id: int, session: Session = Depends(get_session)):
    row = session.get(PriceAlert, alert_id)
    if not row: raise HTTPException(404, "Larmet finns inte")
    session.delete(row); session.commit()


@router.post("/api/v1/devices", status_code=201)
def register_device(data: DeviceTokenCreate, session: Session = Depends(get_session)):
    row=session.exec(select(DeviceToken).where(DeviceToken.token==data.token)).first()
    if row: row.enabled=True;row.platform=data.platform
    else: row=DeviceToken(token=data.token,platform=data.platform)
    session.add(row);session.commit();session.refresh(row);return row

@router.get("/api/v1/notifications/status")
def notification_status(): return {"firebase_ready":firebase_ready()}

@router.get("/api/v1/tickers/{symbol}/notifications")
def product_notifications(symbol: str, session: Session = Depends(get_session)):
    symbol=symbol.upper();signal=session.exec(select(SignalAlert).where(SignalAlert.ticker_symbol==symbol)).first();prices=session.exec(select(PriceAlert).where(PriceAlert.ticker_symbol==symbol)).all()
    return {"signal_enabled":signal.enabled if signal else False,"price_alerts":prices}

@router.put("/api/v1/tickers/{symbol}/notifications/signal")
def update_signal_notification(symbol: str,data: SignalAlertUpdate,session: Session=Depends(get_session)):
    symbol=symbol.upper()
    if not session.get(Ticker,symbol):raise HTTPException(404,"Tickern finns inte")
    row=session.exec(select(SignalAlert).where(SignalAlert.ticker_symbol==symbol)).first()
    if row:row.enabled=data.enabled
    else:row=SignalAlert(ticker_symbol=symbol,enabled=data.enabled)
    session.add(row);session.commit();session.refresh(row);return row

@router.post("/api/v1/tickers/{symbol}/notifications/price",status_code=201)
def product_price_notification(symbol:str,data:AlertCreate,session:Session=Depends(get_session)):
    symbol=symbol.upper();direction=data.direction.strip()
    if direction not in (">","<"):raise HTTPException(422,"direction måste vara > eller <")
    row=PriceAlert(ticker_symbol=symbol,direction=direction,target_price=data.target_price,enabled=data.enabled,triggered=False,last_condition_met=None);session.add(row);session.commit();session.refresh(row);return row

@router.patch("/api/v1/notifications/price/{alert_id}")
def patch_price_notification(alert_id:int,data:PriceAlertUpdate,session:Session=Depends(get_session)):
    row=session.get(PriceAlert,alert_id)
    if not row:raise HTTPException(404,"Larmet finns inte")
    row.enabled=data.enabled;session.add(row);session.commit();session.refresh(row);return row

@router.delete("/api/v1/notifications/price/{alert_id}",status_code=204)
def remove_price_notification(alert_id:int,session:Session=Depends(get_session)):
    row=session.get(PriceAlert,alert_id)
    if not row:raise HTTPException(404,"Larmet finns inte")
    session.delete(row);session.commit()

@router.get("/api/v1/notifications/active")
def active_notifications(session:Session=Depends(get_session)):
    signals=session.exec(select(SignalAlert).where(SignalAlert.enabled==True)).all();prices=session.exec(select(PriceAlert).where(PriceAlert.enabled==True)).all()
    def ticker_data(symbol):
        row=session.get(Ticker,symbol);return row.model_dump() if row else {"symbol":symbol,"name":symbol}
    return {"firebase_ready":firebase_ready(),"signal_alerts":[{"alert":x.model_dump(),"ticker":ticker_data(x.ticker_symbol)} for x in signals],"price_alerts":[{"alert":x.model_dump(),"ticker":ticker_data(x.ticker_symbol)} for x in prices]}

@router.post("/api/v1/notifications/check")
def check_notifications_now():check_alerts();return {"ok":True}
