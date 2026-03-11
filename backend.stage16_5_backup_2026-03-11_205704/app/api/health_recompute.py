from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])


@router.post("/recompute")
async def recompute_health():
    return {
        "status": "ok",
        "recomputed": True,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Temporary Stage16 compatibility endpoint restored to stop 404s from cron/integrations."
    }
