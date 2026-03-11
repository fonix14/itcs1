from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict, List

import asyncpg
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.portal_l4_parser import parse_portal_l4_xlsx

router = APIRouter(prefix="/api", tags=["portal-l4"])

DATABASE_URL = os.getenv("DATABASE_URL", "")
DSN = (
    DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    .replace("postgres+asyncpg://", "postgres://")
)

PORTAL_L4_CAP = int(os.getenv("PORTAL_L4_CAP", "200"))


def _s(v: Any) -> str:
    if v is None:
        return "—"
    s = str(v).strip()
    return s if s else "—"


def _dt(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v))
    except Exception:
        try:
            return datetime.strptime(str(v), "%Y-%m-%d %H:%M")
        except Exception:
            return None


async def _get_store_id_by_store_no(conn: asyncpg.Connection, store_no: str):
    row = await conn.fetchrow(
        """
        SELECT id
        FROM stores
        WHERE store_no = $1
        LIMIT 1
        """,
        store_no,
    )
    return row["id"] if row else None


@router.post("/portal_l4_uploads")
async def portal_l4_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx accepted")

    if not DSN:
        raise HTTPException(status_code=500, detail="DATABASE_URL is empty")

    content = await file.read()

    try:
        res = parse_portal_l4_xlsx(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")

    tasks: List[Dict[str, Any]] = res.tasks[:PORTAL_L4_CAP]

    inserted = 0
    updated = 0
    skipped = 0

    conn = await asyncpg.connect(DSN)

    try:
        for t in tasks:
            portal_id = str(t.get("portal_task_id") or "").strip()
            if not portal_id:
                skipped += 1
                continue

            store_no = str(t.get("store_no") or "").strip()
            if not store_no:
                skipped += 1
                continue

            store_id = await _get_store_id_by_store_no(conn, store_no)
            if not store_id:
                skipped += 1
                continue

            status = str(t.get("status") or "open").strip() or "open"
            payload = json.dumps(t, ensure_ascii=False)

            sla_due_at = _dt(t.get("sla_date"))
            created_at = _dt(t.get("created_at"))

            exists = await conn.fetchval(
                "SELECT id FROM tasks WHERE portal_task_id = $1",
                portal_id,
            )

            if exists:
                await conn.execute(
                    """
                    UPDATE tasks
                    SET
                        store_id = $2,
                        status = $3,
                        sla_due_at = COALESCE($4::timestamptz, sla_due_at),
                        last_seen_at = now(),
                        payload = $5::jsonb
                    WHERE portal_task_id = $1
                    """,
                    portal_id,
                    store_id,
                    status,
                    sla_due_at,
                    payload,
                )
                updated += 1
            else:
                await conn.execute(
                    """
                    INSERT INTO tasks
                    (
                        portal_task_id,
                        store_id,
                        status,
                        sla_due_at,
                        last_seen_at,
                        payload,
                        created_at
                    )
                    VALUES
                    (
                        $1,
                        $2,
                        $3,
                        $4::timestamptz,
                        now(),
                        $5::jsonb,
                        COALESCE($6::timestamptz, now())
                    )
                    """,
                    portal_id,
                    store_id,
                    status,
                    sla_due_at,
                    payload,
                    created_at,
                )
                inserted += 1

    finally:
        await conn.close()

    return {
        "status": "ok",
        "parsed_total_rows": res.total,
        "invalid_rows": res.invalid,
        "tasks_seen": len(tasks),
        "tasks_inserted": inserted,
        "tasks_updated": updated,
        "tasks_skipped": skipped,
        "headers_detected": getattr(res, "headers", [])[:80],
    }
