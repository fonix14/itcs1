from fastapi import APIRouter, UploadFile, File, HTTPException
from app.importer.service import process_excel_upload

router = APIRouter(prefix="/api", tags=["portal-l4"])


@router.post("/portal_l4_uploads")
async def portal_l4_upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx accepted")

    content = await file.read()
    result = await process_excel_upload(content, file.filename)
    return result
