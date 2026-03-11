import hashlib
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Upload
from app.services.l4_import import process_l4_row
from app.services.trust import calculate_trust_level
from app.services.notifications import enqueue_variant_b

router = APIRouter()


def calculate_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@router.post("/api/tasks_uploads")
async def upload_tasks(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    try:
        content = await file.read()
        file_hash = calculate_file_hash(content)

        upload = Upload(
            file_name=file.filename,
            file_hash=file_hash,
        )
        session.add(upload)
        await session.flush()

        try:
            excel_buffer = BytesIO(content)
            df = pd.read_excel(excel_buffer)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid XLSX file: {e}")

        created = 0
        updated = 0
        invalid = 0
        created_task_ids: list[str] = []

        for _, row in df.iterrows():
            result, task_id = await process_l4_row(session, row.to_dict(), upload.id)

            if result == "created":
                created += 1
                if task_id:
                    created_task_ids.append(task_id)
            elif result == "updated":
                updated += 1
            else:
                invalid += 1

        trust_level = calculate_trust_level(
            created=created,
            updated=updated,
            invalid=invalid,
        )

        upload.trust_level = trust_level

        # commit tasks+upload first (so notifier can safely read)
        await session.commit()

        # Stage 4.3 Variant B:
        # - digest per manager per upload
        # - only NEW tasks as immediate notifications
        await enqueue_variant_b(
            session=session,
            upload_id=upload.id,
            created=created,
            updated=updated,
            invalid=invalid,
            trust=trust_level,
            created_task_ids=created_task_ids,
        )
        await session.commit()

        return {
            "upload_id": str(upload.id),
            "created": created,
            "updated": updated,
            "invalid": invalid,
            "trust_level": trust_level,
            "created_task_ids_count": len(created_task_ids),
            "mode": "B",
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
