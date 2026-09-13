from app.main import app


REQUIRED_ROUTES = {
    "/health",
    "/api/v1/catalog",
    "/api/v1/favorites",
    "/api/v1/market",
    "/api/v1/holdings",
    "/api/v1/notifications/status",
    "/api/v1/notifications/active",
    "/api/v1/notifications/check",
}


def collect_paths(routes):
    paths = set()

    for route in routes:
        path = getattr(route, "path", None)

        if path is not None:
            paths.add(path)

        nested_routes = getattr(route, "routes", None)

        if nested_routes is not None:
            paths.update(collect_paths(nested_routes))

        nested_router = getattr(route, "router", None)

        if nested_router is not None:
            paths.update(collect_paths(nested_router.routes))

    return paths


existing_routes = collect_paths(app.routes)
missing_routes = sorted(REQUIRED_ROUTES - existing_routes)

print("Registrerade routes:")

for path in sorted(existing_routes):
    print(f"  {path}")

if missing_routes:
    raise SystemExit(f"Saknade routes: {missing_routes}")

print()
print(f"[OK] {len(existing_routes)} API-routes registrerade.")
print("[OK] Kritiska routes finns kvar.")