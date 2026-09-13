"""Firebase delivery and five-minute alert worker."""
import os, threading
from pathlib import Path
from sqlmodel import Session, select
from .database import engine
from .market import snapshot_dict
from .models import DeviceToken, NotificationEvent, PriceAlert, SignalAlert, Ticker
_stop=threading.Event(); _thread=None

def _firebase_app():
    path=os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if not path or not Path(path).is_file(): return None
    import firebase_admin
    from firebase_admin import credentials
    if not firebase_admin._apps: firebase_admin.initialize_app(credentials.Certificate(path))
    return firebase_admin.get_app()

def firebase_ready():
    try: return _firebase_app() is not None
    except Exception as exc:
        print(f"Firebase init failed: {exc}"); return False

def _send(title, body, symbol):
    if _firebase_app() is None: return
    from firebase_admin import messaging
    with Session(engine) as session: devices=session.exec(select(DeviceToken).where(DeviceToken.enabled==True)).all()
    for device in devices:
        try: messaging.send(messaging.Message(notification=messaging.Notification(title=title,body=body),data={"symbol":symbol},token=device.token,android=messaging.AndroidConfig(priority="high")))
        except Exception as exc: print(f"FCM failed: {exc}")

def _once(session,key,symbol,kind,title,body):
    if session.exec(select(NotificationEvent).where(NotificationEvent.event_key==key)).first(): return False
    session.add(NotificationEvent(ticker_symbol=symbol,event_key=key,kind=kind,title=title,body=body));session.commit();return True

def check_alerts():
    """Send once per crossing and rearm after price returns across the level."""
    from datetime import datetime, timezone
    with Session(engine) as session:
        signals = session.exec(select(SignalAlert).where(SignalAlert.enabled == True)).all()
        prices = session.exec(select(PriceAlert).where(PriceAlert.enabled == True)).all()
        symbols = {item.ticker_symbol for item in signals} | {item.ticker_symbol for item in prices}
        for symbol in symbols:
            try:
                data = snapshot_dict(symbol, True)
            except Exception as exc:
                print(f"Alert check {symbol}: {exc}")
                continue
            ticker = session.get(Ticker, symbol)
            name = ticker.name if ticker else symbol

            signal = next((item for item in signals if item.ticker_symbol == symbol), None)
            if signal:
                current = data["signal"]
                if signal.last_notified_signal is None:
                    signal.last_notified_signal = current
                elif signal.last_notified_signal != current:
                    old = signal.last_notified_signal
                    key = f"signal:{symbol}:{old}:{current}:{data.get('signal_since')}"
                    title = f"{name} har ändrat indikator"
                    body = f"{old} → {current}"
                    if _once(session, key, symbol, "signal", title, body):
                        _send(title, body, symbol)
                    signal.last_notified_signal = current
                session.add(signal)

            current_price = float(data["price"])
            for alert in (item for item in prices if item.ticker_symbol == symbol):
                condition_met = (
                    current_price >= alert.target_price
                    if alert.direction == ">"
                    else current_price <= alert.target_price
                )
                if condition_met and not alert.triggered:
                    now = datetime.now(timezone.utc)
                    key = f"price:{alert.id}:{now.isoformat()}"
                    title = f"{name} har nått prisnivån"
                    body = f"{alert.direction} {alert.target_price:g}. Aktuellt: {current_price:g}"
                    if _once(session, key, symbol, "price", title, body):
                        _send(title, body, symbol)
                    alert.triggered = True
                    alert.triggered_at = now
                elif not condition_met and alert.triggered:
                    alert.triggered = False
                    alert.triggered_at = None
                alert.last_condition_met = condition_met
                session.add(alert)
            session.commit()

def start_worker(interval_seconds=300):
    global _thread
    if _thread and _thread.is_alive(): return
    _stop.clear()
    def loop():
        while not _stop.wait(interval_seconds): check_alerts()
    _thread=threading.Thread(target=loop,daemon=True,name='notification-worker');_thread.start()

def stop_worker(): _stop.set()
