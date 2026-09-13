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
from .routers import health, holdings, market, notifications, tickers

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
app.include_router(tickers.router)
app.include_router(holdings.router)
app.include_router(notifications.router)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origin_list,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

from .services.market_payload import market_payload
