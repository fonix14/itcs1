from fastapi import FastAPI

from app.api import router as api_router
from app.ui import router as ui_router

app = FastAPI(title="ITCS API", version="4.0.0")

# UI без префикса
app.include_router(ui_router)

# Твой текущий API как есть (у тебя он уже с /api внутри, поэтому в Swagger видно /api/api/*)
app.include_router(api_router, prefix="/api")


@app.get("/ping")
async def ping():
    return {"ok": True, "service": "api"}
