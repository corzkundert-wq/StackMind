from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc
from src.backend.database import get_db
from src.backend.models import SavedContent, ContentType
from src.backend.schemas import SaveContentRequest, SavedContentOut, UpdateSavedContentRequest
from typing import Optional

router = APIRouter(prefix="/archive", tags=["archive"])

@router.get("")
def list_saved_content(
    content_type: Optional[str] = Query(None),
    folder: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: DBSession = Depends(get_db),
):
    q = db.query(SavedContent)
    if content_type:
        q = q.filter(SavedContent.content_type == content_type)
    if folder:
        q = q.filter(SavedContent.folder == folder)
    if status:
        q = q.filter(SavedContent.status == status)
    items = q.order_by(desc(SavedContent.created_at)).all()
    results = []
    for i in items:
        results.append({
            "id": str(i.id),
            "content_type": i.content_type.value if hasattr(i.content_type, 'value') else str(i.content_type),
            "title": i.title or "",
            "body": i.body or "",
            "meta": i.meta or {},
            "folder": i.folder or "General",
            "status": i.status or "saved",
            "session_id": str(i.session_id) if i.session_id else None,
            "created_at": i.created_at.isoformat() if i.created_at else "",
            "updated_at": i.updated_at.isoformat() if i.updated_at else "",
        })
    return results

@router.get("/folders")
def list_folders(db: DBSession = Depends(get_db)):
    folders = db.query(SavedContent.folder).distinct().all()
    return sorted(set(f[0] for f in folders if f[0]))

@router.get("/stats")
def archive_stats(db: DBSession = Depends(get_db)):
    total = db.query(SavedContent).count()
    by_type = {}
    for ct in ContentType:
        count = db.query(SavedContent).filter(SavedContent.content_type == ct.value).count()
        if count > 0:
            by_type[ct.value] = count
    all_items = db.query(SavedContent).all()
    folder_counts = {}
    for item in all_items:
        f = item.folder or "General"
        folder_counts[f] = folder_counts.get(f, 0) + 1
    return {"total": total, "by_type": by_type, "by_folder": folder_counts}

@router.post("")
def save_content(req: SaveContentRequest, db: DBSession = Depends(get_db)):
    item = SavedContent(
        content_type=req.content_type,
        title=req.title,
        body=req.body,
        meta=req.meta,
        folder=req.folder,
        session_id=req.session_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": str(item.id),
        "content_type": item.content_type.value if hasattr(item.content_type, 'value') else str(item.content_type),
        "title": item.title or "",
        "body": item.body or "",
        "meta": item.meta or {},
        "folder": item.folder or "General",
        "status": item.status or "saved",
        "session_id": str(item.session_id) if item.session_id else None,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }

@router.patch("/{item_id}")
def update_saved_content(item_id: str, req: UpdateSavedContentRequest, db: DBSession = Depends(get_db)):
    item = db.query(SavedContent).filter(SavedContent.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if req.title is not None:
        item.title = req.title
    if req.body is not None:
        item.body = req.body
    if req.folder is not None:
        item.folder = req.folder
    if req.status is not None:
        item.status = req.status
    if req.meta is not None:
        item.meta = req.meta
    db.commit()
    db.refresh(item)
    return {
        "id": str(item.id),
        "content_type": item.content_type.value if hasattr(item.content_type, 'value') else str(item.content_type),
        "title": item.title or "",
        "body": item.body or "",
        "meta": item.meta or {},
        "folder": item.folder or "General",
        "status": item.status or "saved",
        "session_id": str(item.session_id) if item.session_id else None,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }

@router.delete("/{item_id}")
def delete_saved_content(item_id: str, db: DBSession = Depends(get_db)):
    item = db.query(SavedContent).filter(SavedContent.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted"}
