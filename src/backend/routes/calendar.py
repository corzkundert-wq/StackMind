from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from src.backend.database import get_db
from src.backend.models import CalendarEntry
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import re

router = APIRouter(prefix="/calendar", tags=["calendar"])

class CalendarCreate(BaseModel):
    title: str
    content_type: str = "post"
    scheduled_date: str
    scheduled_time: str = "09:00"
    platform: str = ""
    notes: str = ""
    content_preview: str = ""
    color: str = "blue"
    session_id: Optional[str] = None
    meta: dict = {}

    @field_validator("scheduled_time")
    @classmethod
    def validate_time(cls, v):
        if v and re.match(r'^\d{1,2}:\d{2}$', v):
            return v if len(v) == 5 else f"0{v}"
        m = re.search(r'(\d{1,2}:\d{2})', v or "")
        if m:
            t = m.group(1)
            return t if len(t) == 5 else f"0{t}"
        return "09:00"

class CalendarUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    platform: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    content_preview: Optional[str] = None
    color: Optional[str] = None
    meta: Optional[dict] = None

class CalendarOut(BaseModel):
    id: str
    title: str
    content_type: str
    scheduled_date: str
    scheduled_time: str
    platform: str
    status: str
    notes: str
    content_preview: str
    color: str
    meta: dict
    session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

@router.get("")
def list_entries(month: Optional[str] = None, status: Optional[str] = None, db: DBSession = Depends(get_db)):
    q = db.query(CalendarEntry).order_by(CalendarEntry.scheduled_date, CalendarEntry.scheduled_time)
    if month:
        q = q.filter(CalendarEntry.scheduled_date.like(f"{month}%"))
    if status:
        q = q.filter(CalendarEntry.status == status)
    entries = q.all()
    results = []
    for e in entries:
        results.append({
            "id": str(e.id), "title": e.title, "content_type": e.content_type,
            "scheduled_date": e.scheduled_date, "scheduled_time": e.scheduled_time,
            "platform": e.platform, "status": e.status, "notes": e.notes,
            "content_preview": e.content_preview, "color": e.color,
            "meta": e.meta or {}, "session_id": str(e.session_id) if e.session_id else None,
            "created_at": e.created_at.isoformat() if e.created_at else "",
            "updated_at": e.updated_at.isoformat() if e.updated_at else "",
        })
    return results

@router.post("")
def create_entry(req: CalendarCreate, db: DBSession = Depends(get_db)):
    entry = CalendarEntry(
        title=req.title,
        content_type=req.content_type,
        scheduled_date=req.scheduled_date,
        scheduled_time=req.scheduled_time,
        platform=req.platform,
        notes=req.notes,
        content_preview=req.content_preview,
        color=req.color,
        meta=req.meta,
        session_id=req.session_id if req.session_id else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": str(entry.id), "title": entry.title, "scheduled_date": entry.scheduled_date, "status": entry.status}

@router.patch("/{entry_id}")
def update_entry(entry_id: str, req: CalendarUpdate, db: DBSession = Depends(get_db)):
    entry = db.query(CalendarEntry).filter(CalendarEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    for field in ["title", "scheduled_date", "scheduled_time", "platform", "status", "notes", "content_preview", "color", "meta"]:
        val = getattr(req, field)
        if val is not None:
            setattr(entry, field, val)
    db.commit()
    db.refresh(entry)
    return {"id": str(entry.id), "title": entry.title, "status": entry.status}

@router.delete("/{entry_id}")
def delete_entry(entry_id: str, db: DBSession = Depends(get_db)):
    entry = db.query(CalendarEntry).filter(CalendarEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"status": "deleted"}

@router.post("/ai_suggest")
def ai_suggest_schedule(req: dict, db: DBSession = Depends(get_db)):
    from src.backend.services.llm_service import call_llm
    posts = req.get("posts", [])
    if not posts:
        raise HTTPException(status_code=400, detail="No posts provided")

    post_summaries = []
    for i, p in enumerate(posts):
        title = p.get("series_label", p.get("title", f"Post {i+1}"))
        platform = p.get("platform", "LinkedIn")
        post_summaries.append(f"- {title} ({platform})")

    prompt = f"""You are a social media strategist. Given these content pieces, suggest an optimal publishing schedule over the next 2 weeks starting from today.

Content pieces:
{chr(10).join(post_summaries)}

For each piece, suggest:
1. Best day and time to publish (format: YYYY-MM-DD, HH:MM)
2. Why that timing works
3. A color tag (blue, green, orange, purple, red, teal)

Return as JSON array:
[{{"title": "...", "scheduled_date": "YYYY-MM-DD", "scheduled_time": "HH:MM", "reason": "...", "color": "blue"}}]

Today's date is {datetime.now().strftime('%Y-%m-%d')}. Consider:
- LinkedIn: Tue-Thu mornings (8-10 AM) best
- Twitter/X: Weekdays, multiple times ok
- Blog: Mon or Wed mornings
- Space posts 1-2 days apart for series
"""
    result = call_llm(prompt, response_format="json")
    if isinstance(result, list):
        return {"suggestions": result}
    elif isinstance(result, dict) and "suggestions" in result:
        return result
    return {"suggestions": result if isinstance(result, list) else []}
