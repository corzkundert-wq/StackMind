import json
from pydantic import BaseModel
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File as FastAPIFile
from sqlalchemy.orm import Session as DBSession
from src.backend.database import get_db
from src.backend.models import File, FileStatus
from src.backend.services.file_service import save_upload, process_file, process_text_paste

router = APIRouter(prefix="/files", tags=["files"])

class PasteTextRequest(BaseModel):
    library_id: str
    title: str = "Pasted Text"
    text: str
    tags: List[str] = []

@router.post("/upload")
async def upload_file(
    library_id: str = Form(...),
    file: UploadFile = FastAPIFile(...),
    tags: str = Form("[]"),
    db: DBSession = Depends(get_db),
):
    try:
        tags_list = json.loads(tags) if tags else []
    except Exception:
        tags_list = []

    content = await file.read()
    filepath = save_upload(content, file.filename)

    file_record = File(
        library_id=library_id,
        filename=file.filename,
        display_name=file.filename,
        tags=tags_list,
        status=FileStatus.uploaded,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    try:
        process_file(db, file_record, filepath)
    except Exception as e:
        pass

    db.refresh(file_record)
    return {
        "id": str(file_record.id),
        "filename": file_record.filename,
        "status": file_record.status.value,
        "error": file_record.error,
    }

@router.get("")
def list_files(library_id: str = None, db: DBSession = Depends(get_db)):
    q = db.query(File)
    if library_id:
        q = q.filter(File.library_id == library_id)
    files = q.order_by(File.uploaded_at.desc()).all()
    return [
        {
            "id": str(f.id),
            "library_id": str(f.library_id),
            "filename": f.filename,
            "display_name": f.display_name,
            "status": f.status.value,
            "tags": f.tags or [],
            "uploaded_at": str(f.uploaded_at),
            "error": f.error,
        }
        for f in files
    ]

@router.post("/paste")
def paste_text(req: PasteTextRequest, db: DBSession = Depends(get_db)):
    try:
        file_record = process_text_paste(db, req.library_id, req.title, req.text, req.tags)
        return {
            "id": str(file_record.id),
            "filename": file_record.filename,
            "display_name": file_record.display_name,
            "status": file_record.status.value,
            "error": file_record.error,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{file_id}")
def get_file(file_id: str, db: DBSession = Depends(get_db)):
    f = db.query(File).filter(File.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "id": str(f.id),
        "library_id": str(f.library_id),
        "filename": f.filename,
        "display_name": f.display_name,
        "status": f.status.value,
        "tags": f.tags or [],
        "raw_text": (f.raw_text or "")[:2000],
        "uploaded_at": str(f.uploaded_at),
        "error": f.error,
    }
