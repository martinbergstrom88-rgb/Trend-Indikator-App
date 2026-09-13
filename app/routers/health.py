from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health(request: Request):
    return {
        "status": "ok",
        "service": "Trend Indikator API",
        "version": request.app.version,
    }
