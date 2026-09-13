from app.main import app

required = {
    "/health",
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
