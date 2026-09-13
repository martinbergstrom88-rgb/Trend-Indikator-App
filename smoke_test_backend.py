from app.main import app

REQUIRED_ROUTES = {
    '/health',
    '/api/v1/catalog',
    '/api/v1/favorites',
    '/api/v1/market',
    '/api/v1/tickers',
    '/api/v1/tickers/{symbol}',
    '/api/v1/holdings',
    '/api/v1/holdings/{symbol}',
    '/api/v1/notifications/status',
    '/api/v1/notifications/active',
    '/api/v1/notifications/check',
}

existing_routes = set(app.openapi()['paths'])
missing_routes = sorted(REQUIRED_ROUTES - existing_routes)

print('Registrerade routes:')
for path in sorted(existing_routes):
    print(f'  {path}')

if missing_routes:
    raise SystemExit(f'Saknade routes: {missing_routes}')

print()
print(f'[OK] {len(existing_routes)} API-routes registrerade.')
print('[OK] Kritiska routes finns kvar.')
