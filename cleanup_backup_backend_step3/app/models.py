from datetime import date, datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel

class Ticker(SQLModel, table=True):
    symbol: str = Field(primary_key=True, max_length=40)
    name: str = Field(default="", max_length=120)
    asset_type: str = Field(default="stock", max_length=20, index=True)
    currency: Optional[str] = Field(default=None, max_length=10)
    tradingview_symbol: Optional[str] = Field(default=None, max_length=80)
    is_favorite: bool = Field(default=False, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Holding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker_symbol: str = Field(foreign_key="ticker.symbol", unique=True, index=True)
    quantity: float = Field(gt=0)
    purchase_price: float = Field(gt=0)
    purchase_date: Optional[date] = None

class PriceAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker_symbol: str = Field(foreign_key="ticker.symbol", index=True)
    direction: str = Field(max_length=5)
    target_price: float = Field(gt=0)
    enabled: bool = True
    triggered: bool = False
    last_condition_met: Optional[bool] = None
    triggered_at: Optional[datetime] = None

class SignalHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker_symbol: str = Field(foreign_key="ticker.symbol", index=True)
    old_signal: Optional[str] = Field(default=None, max_length=10)
    new_signal: str = Field(max_length=10)
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True, max_length=50)
    value: str = Field(max_length=500)

class TickerCreate(SQLModel):
    symbol: str
    name: str = ""
    asset_type: str = "stock"
    currency: Optional[str] = None
    tradingview_symbol: Optional[str] = None
    is_favorite: bool = False

class TickerPatch(SQLModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    currency: Optional[str] = None
    tradingview_symbol: Optional[str] = None
    is_favorite: Optional[bool] = None
    is_active: Optional[bool] = None

class HoldingUpsert(SQLModel):
    quantity: float = Field(gt=0)
    purchase_price: float = Field(gt=0)
    purchase_date: Optional[date] = None

class AlertCreate(SQLModel):
    ticker_symbol: str
    direction: str
    target_price: float = Field(gt=0)
    enabled: bool = True


class DeviceToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True, max_length=512)
    platform: str = Field(default="android", max_length=20)
    enabled: bool = True
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SignalAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker_symbol: str = Field(foreign_key="ticker.symbol", unique=True, index=True)
    enabled: bool = True
    last_notified_signal: Optional[str] = Field(default=None, max_length=10)

class NotificationEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker_symbol: str = Field(index=True)
    event_key: str = Field(unique=True, index=True, max_length=180)
    kind: str = Field(max_length=20)
    title: str = Field(max_length=160)
    body: str = Field(max_length=500)
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeviceTokenCreate(SQLModel):
    token: str
    platform: str = "android"

class SignalAlertUpdate(SQLModel):
    enabled: bool

class PriceAlertUpdate(SQLModel):
    enabled: bool
