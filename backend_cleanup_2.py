from pathlib import Path
import shutil

ROOT = Path.cwd()
APP = ROOT / "app"
MAIN = APP / "main.py"
BACKUP = ROOT / "cleanup_backup_backend_step2"
ROUTERS = APP / "routers"

if not MAIN.is_file():
    raise SystemExit("Hittar inte app/main.py. Kor scriptet fran backendprojektets rot.")
if BACKUP.exists():
    raise SystemExit(f"Backup finns redan: {BACKUP}")

text = MAIN.read_text(encoding="utf-8")
anchors = [
    ("health.py", '@app.get("/health")'),
    ("market.py", '@app.get("/api/v1/catalog")'),
    ("tickers.py", '@app.get("/api/v1/tickers/{symbol}")'),
    ("holdings.py", '@app.get("/api/v1/holdings")'),
    ("notifications.py", '@app.get("/api/v1/alerts")'),
]
positions = []
for filename, anchor in anchors:
    pos = text.find(anchor)
    if pos < 0:
        raise SystemExit(f"Avbryter utan andringar. Hittar inte {anchor!r}")
    positions.append((filename, anchor, pos))
if positions != sorted(positions, key=lambda item: item[2]):
    raise SystemExit("Avbryter. Routes ligger inte i forvantad ordning.")

shutil.copytree(APP, BACKUP / "app")
ROUTERS.mkdir(exist_ok=True)
(ROUTERS / "__init__.py").write_text("", encoding="utf-8")

common = '''from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..currency import rate_to_sek
from ..database import get_session
from ..market import snapshot_dict
from ..models import (
    AlertCreate,
    AppSetting,
    DeviceToken,
    DeviceTokenCreate,
    Holding,
    HoldingUpsert,
    PriceAlert,
    PriceAlertUpdate,
    SignalAlert,
    SignalAlertUpdate,
    SignalHistory,
    Ticker,
    TickerCreate,
    TickerPatch,
)
from ..notifications import check_alerts, firebase_ready
from ..services.market_payload import market_payload

router = APIRouter()

'''

for index, (filename, _, start) in enumerate(positions):
    end = positions[index + 1][2] if index + 1 < len(positions) else len(text)
    body = text[start:end].strip().replace("@app.", "@router.")
    (ROUTERS / filename).write_text(common + body + "\n", encoding="utf-8")

# Keep startup, app construction and CORS in main.py. Remove all route bodies.
preamble = text[:positions[0][2]].rstrip()
# Remove route-only imports from the preamble and add router imports.
preamble = preamble.replace("from fastapi import Depends, FastAPI, HTTPException, Query", "from fastapi import FastAPI")
preamble = preamble.replace("from sqlmodel import Session, select, delete", "from sqlmodel import Session")
preamble = preamble.replace("from .market import snapshot_dict\n", "")
preamble = preamble.replace("from .currency import rate_to_sek\n", "")
preamble = preamble.replace("from .services.market_payload import market_payload\n", "")
model_start = preamble.find("from .models import (")
if model_start >= 0:
    model_end = preamble.find(")", model_start)
    if model_end >= 0:
        preamble = preamble[:model_start] + preamble[model_end + 1:]

router_imports = '''
from .routers import health, holdings, market, notifications, tickers
'''
includes = '''
app.include_router(health.router)
app.include_router(market.router)
app.include_router(tickers.router)
app.include_router(holdings.router)
app.include_router(notifications.router)
'''
insert_at = preamble.find("@asynccontextmanager")
preamble = preamble[:insert_at] + router_imports + "\n" + preamble[insert_at:]
new_main = preamble.strip() + "\n\n" + includes
MAIN.write_text(new_main, encoding="utf-8")

smoke = '''from app.main import app

required = {
    "/health",
    "/api/v1/catalog",
    "/api/v1/favorites",
    "/api/v1/market",
    "/api/v1/holdings",
    "/api/v1/notifications/status",
    "/api/v1/notifications/active",
    "/api/v1/notifications/check",
}
existing = {route.path for route in app.routes}
missing = sorted(required - existing)
if missing:
    raise SystemExit(f"Saknade routes: {missing}")
print(f"[OK] {len(existing)} routes registrerade.")
print("[OK] Kritiska routes finns kvar.")
'''
(ROOT / "smoke_test_backend.py").write_text(smoke, encoding="utf-8")

print("[OK] Backend Cleanup steg 2 ar klart.")
print(f"[OK] Backup: {BACKUP}")
print("[NEXT] python -m compileall app")
print("[NEXT] python smoke_test_backend.py")
