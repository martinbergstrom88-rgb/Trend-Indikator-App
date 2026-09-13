from pathlib import Path
import shutil

ROOT = Path.cwd()
APP = ROOT / "app"
MAIN = APP / "main.py"
ROUTERS = APP / "routers"
BACKUP = ROOT / "cleanup_backup_backend_step3"

if not MAIN.is_file():
    raise SystemExit("Hittar inte app/main.py. Kor scriptet fran backendprojektets rot.")
if BACKUP.exists():
    raise SystemExit(f"Backup finns redan: {BACKUP}")

text = MAIN.read_text(encoding="utf-8")
health_anchor = '@app.get("/health")'
next_anchor = '@app.get("/api/v1/catalog")'

start = text.find(health_anchor)
end = text.find(next_anchor, start)
if start < 0 or end < 0:
    raise SystemExit(
        "Avbryter utan andringar. Hittar inte health-routen eller catalog-routen."
    )

shutil.copytree(APP, BACKUP / "app")
ROUTERS.mkdir(exist_ok=True)
(ROUTERS / "__init__.py").touch()

health_body = text[start:end].strip().replace("@app.", "@router.", 1)
health_file = '''from fastapi import APIRouter, Request

router = APIRouter()


''' + health_body.replace(
    'def health(): return {"status": "ok", "service": "Trend Indikator API", "version": app.version}',
    'def health(request: Request):\n    return {\n        "status": "ok",\n        "service": "Trend Indikator API",\n        "version": request.app.version,\n    }',
) + "\n"
(ROUTERS / "health.py").write_text(health_file, encoding="utf-8")

# Remove only the health route from main.py.
text = text[:start].rstrip() + "\n\n" + text[end:]

# Import the health router module.
import_line = "from .routers import health\n"
if import_line not in text:
    marker = "from .notifications import firebase_ready, start_worker, stop_worker, check_alerts\n"
    if marker not in text:
        raise SystemExit("Avbryter. Hittar inte importplatsen i app/main.py.")
    text = text.replace(marker, marker + import_line, 1)

# Register exactly one router. Appending is valid because app already exists.
include_line = "app.include_router(health.router)"
if include_line not in text:
    text = text.rstrip() + "\n\n" + include_line + "\n"

MAIN.write_text(text, encoding="utf-8")

print("[OK] Endast /health flyttades till app/routers/health.py.")
print(f"[OK] Backup: {BACKUP}")
print("[NEXT] python -m compileall app")
print("[NEXT] python smoke_test_backend.py")
