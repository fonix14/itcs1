from __future__ import annotations

import os
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, Optional

import asyncpg

from app.services.portal_l4_parser import parse_portal_l4_xlsx

DATABASE_URL = os.getenv("DATABASE_URL", "")
DSN = (
    DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    .replace("postgres+asyncpg://", "postgres://")
)

DEFAULT_PROFILE_ID = "portal_l4"


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    s = str(value).strip()
    if not s or s == "—" or s.lower() == "nan":
        return None

    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue

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


async def process_excel_upload(content: bytes, filename: str = "ui_upload.xlsx") -> Dict[str, Any]:
    if not content:
        raise ValueError("empty upload content")

    if not DSN:
        raise RuntimeError("DATABASE_URL is empty")

    parsed = parse_portal_l4_xlsx(content)
    file_hash = _sha256_bytes(content)

    total_rows = int(parsed.total or 0)
    parser_invalid_rows = int(parsed.invalid or 0)

    conn = await asyncpg.connect(DSN)

    try:
        existing_upload_id = await conn.fetchval(
            """
            SELECT id
            FROM uploads
            WHERE file_hash = $1
              AND profile_id = $2
            LIMIT 1
            """,
            file_hash,
            DEFAULT_PROFILE_ID,
        )

        if existing_upload_id:
            return {
                "status": "ok",
                "idempotent": True,
                "upload_id": str(existing_upload_id),
                "total_rows": total_rows,
                "valid_rows": 0,
                "invalid_rows": parser_invalid_rows,
                "seen_tasks_count": 0,
                "tasks_inserted": 0,
                "tasks_updated": 0,
                "tasks_skipped": 0,
            }

        upload_id = await conn.fetchval(
            """
            INSERT INTO uploads
            (
                file_name,
                file_hash,
                profile_id,
                uploaded_at,
                total_rows,
                valid_rows,
                invalid_rows,
                invalid_ratio,
                seen_tasks_count,
                meta
            )
            VALUES
            (
                $1,
                $2,
                $3,
                now(),
                $4,
                0,
                0,
                0,
                0,
                $5::jsonb
            )
            RETURNING id
            """,
            filename,
            file_hash,
            DEFAULT_PROFILE_ID,
            total_rows,
            json.dumps({"headers": getattr(parsed, "headers", [])}, ensure_ascii=False),
        )

        inserted = 0
        updated = 0
        skipped = 0
        valid_rows = 0
        import_error_rows = 0

        for idx, task in enumerate(parsed.tasks, start=1):
            try:
                portal_task_id = str(task.get("portal_task_id") or "").strip()
                store_no = str(task.get("store_no") or "").strip()

                if not portal_task_id:
                    import_error_rows += 1
                    await conn.execute(
                        """
                        INSERT INTO import_errors (upload_id, row_number, error, raw, created_at)
                        VALUES ($1, $2, $3, $4::jsonb, now())
                        """,
                        upload_id,
                        idx,
                        "portal_task_id is empty",
                        json.dumps(task, ensure_ascii=False),
                    )
                    continue

                if not store_no:
                    import_error_rows += 1
                    await conn.execute(
                        """
                        INSERT INTO import_errors (upload_id, row_number, error, raw, created_at)
                        VALUES ($1, $2, $3, $4::jsonb, now())
                        """,
                        upload_id,
                        idx,
                        "store_no is empty",
                        json.dumps(task, ensure_ascii=False),
                    )
                    continue

                store_id = await _get_store_id_by_store_no(conn, store_no)
                if not store_id:
                    skipped += 1
                    import_error_rows += 1
                    await conn.execute(
                        """
                        INSERT INTO import_errors (upload_id, row_number, error, raw, created_at)
                        VALUES ($1, $2, $3, $4::jsonb, now())
                        """,
                        upload_id,
                        idx,
                        f"store not found: {store_no}",
                        json.dumps(task, ensure_ascii=False),
                    )
                    continue

                sla_due_at = _to_dt(task.get("sla_date"))
                payload = json.dumps(task, ensure_ascii=False)

                existing_task_id = await conn.fetchval(
                    """
                    SELECT id
                    FROM tasks
                    WHERE portal_task_id = $1
                    LIMIT 1
                    """,
                    portal_task_id,
                )

                if existing_task_id:
                    await conn.execute(
                        """
                        UPDATE tasks
                        SET
                            store_id = $2,
                            status = 'open',
                            sla_due_at = COALESCE($3::timestamptz, sla_due_at),
                            last_seen_at = now(),
                            payload = $4::jsonb,
                            upload_id = $5,
                            updated_at = now()
                        WHERE portal_task_id = $1
                        """,
                        portal_task_id,
                        store_id,
                        sla_due_at,
                        payload,
                        upload_id,
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
                            upload_id,
                            created_at,
                            updated_at
                        )
                        VALUES
                        (
                            $1,
                            $2,
                            'open',
                            $3::timestamptz,
                            now(),
                            $4::jsonb,
                            $5,
                            now(),
                            now()
                        )
                        """,
                        portal_task_id,
                        store_id,
                        sla_due_at,
                        payload,
                        upload_id,
                    )
                    inserted += 1

                valid_rows += 1

            except Exception as row_error:
                import_error_rows += 1
                await conn.execute(
                    """
                    INSERT INTO import_errors (upload_id, row_number, error, raw, created_at)
                    VALUES ($1, $2, $3, $4::jsonb, now())
                    """,
                    upload_id,
                    idx,
                    str(row_error),
                    json.dumps(task, ensure_ascii=False),
                )

        invalid_rows = parser_invalid_rows + import_error_rows + skipped
        seen_tasks_count = inserted + updated
        invalid_ratio = (invalid_rows / total_rows) if total_rows else 0

        await conn.execute(
            """
            UPDATE uploads
            SET
                valid_rows = $2,
                invalid_rows = $3,
                invalid_ratio = $4,
                seen_tasks_count = $5
            WHERE id = $1
            """,
            upload_id,
            valid_rows,
            invalid_rows,
            invalid_ratio,
            seen_tasks_count,
        )

        await conn.execute(
            """
            INSERT INTO upload_metrics
            (
                upload_id,
                baseline_seen,
                abs_drop,
                rel_drop,
                coverage_drop,
                created_at
            )
            VALUES
            (
                $1,
                NULL,
                NULL,
                NULL,
                FALSE,
                now()
            )
            ON CONFLICT (upload_id) DO NOTHING
            """,
            upload_id,
        )

        return {
            "status": "ok",
            "idempotent": False,
            "upload_id": str(upload_id),
            "total_rows": total_rows,
            "valid_rows": valid_rows,
            "invalid_rows": invalid_rows,
            "seen_tasks_count": seen_tasks_count,
            "tasks_inserted": inserted,
            "tasks_updated": updated,
            "tasks_skipped": skipped,
        }

    finally:
        await conn.close()
