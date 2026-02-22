import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from src.backend.database import get_db
from src.backend.models import Session, Artifact, ArtifactItem, Vote, Pin, VoteType, Approval
from src.backend.schemas import SessionCreate, VoteRequest, PinRequest, ModuleRunRequest
from src.backend.schemas import DeckBuilderRequest, ContentSeriesRequest, EmailRequest, VideoRequest
from src.backend.schemas import ApprovalUpdateRequest, WebhookRequest, ExportRequest, BlogSeriesRequest
from src.backend.services.module_service import run_module
from src.backend.services.action_service import (
    export_session, generate_deck, generate_content_series,
    generate_email_sequence, run_video_pipeline,
    update_approval_status, send_webhook, generate_post_image,
    generate_blog_series, consolidate_summary, suggest_thesis,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("")
def create_session(req: SessionCreate, db: DBSession = Depends(get_db)):
    session = Session(
        identity_id=req.identity_id,
        library_id=req.library_id,
        selected_file_ids=req.selected_file_ids,
        selection_mode=req.selection_mode,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": str(session.id), "created_at": str(session.created_at)}

@router.get("/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    s = db.query(Session).filter(Session.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    artifacts = db.query(Artifact).filter(Artifact.session_id == session_id).all()
    return {
        "id": str(s.id),
        "identity_id": str(s.identity_id),
        "library_id": str(s.library_id),
        "selected_file_ids": s.selected_file_ids,
        "created_at": str(s.created_at),
        "artifacts": [
            {
                "id": str(a.id),
                "module_name": a.module_name,
                "created_at": str(a.created_at),
                "item_count": db.query(ArtifactItem).filter(ArtifactItem.artifact_id == a.id).count(),
            }
            for a in artifacts
        ],
    }

@router.get("/{session_id}/available_modules")
def get_available_modules(session_id: str, db: DBSession = Depends(get_db)):
    analysis_modules = ["summary", "signals", "claims", "evidence", "relevance", "durability", "leverage", "canon", "decision_memo", "market_trends"]
    artifacts = db.query(Artifact).filter(Artifact.session_id == session_id).all()
    run_modules = list(set(a.module_name for a in artifacts if a.module_name in analysis_modules))
    return {"available_modules": run_modules}

MODULES = ["summary", "signals", "claims", "evidence", "relevance", "durability", "leverage", "canon", "decision_memo", "market_trends"]

for mod in MODULES:
    def make_route(module_name):
        @router.post(f"/{{session_id}}/run/{module_name}")
        def run_mod(session_id: str, req: ModuleRunRequest = None, db: DBSession = Depends(get_db), _mod=module_name):
            if req is None:
                req = ModuleRunRequest()
            try:
                return run_module(db, session_id, _mod, req.top_k, req.use_all_chunks, req.params)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        return run_mod
    make_route(mod)

@router.post("/{session_id}/vote")
def vote(session_id: str, req: VoteRequest, db: DBSession = Depends(get_db)):
    v = Vote(
        session_id=session_id,
        artifact_item_id=req.artifact_item_id,
        vote=VoteType(req.vote),
        note=req.note,
    )
    db.add(v)
    db.commit()
    return {"status": "ok", "vote_id": str(v.id)}

@router.post("/{session_id}/pin")
def pin(session_id: str, req: PinRequest, db: DBSession = Depends(get_db)):
    existing = db.query(Pin).filter(
        Pin.session_id == session_id, Pin.artifact_item_id == req.artifact_item_id
    ).first()
    if existing:
        return {"status": "already_pinned"}
    p = Pin(session_id=session_id, artifact_item_id=req.artifact_item_id)
    db.add(p)
    db.commit()
    return {"status": "pinned", "pin_id": str(p.id)}

@router.post("/{session_id}/unpin")
def unpin(session_id: str, req: PinRequest, db: DBSession = Depends(get_db)):
    p = db.query(Pin).filter(
        Pin.session_id == session_id, Pin.artifact_item_id == req.artifact_item_id
    ).first()
    if p:
        db.delete(p)
        db.commit()
    return {"status": "unpinned"}

@router.get("/{session_id}/pins")
def get_pins(session_id: str, db: DBSession = Depends(get_db)):
    pins = db.query(Pin).filter(Pin.session_id == session_id).all()
    result = []
    for p in pins:
        item = db.query(ArtifactItem).filter(ArtifactItem.id == p.artifact_item_id).first()
        if item:
            result.append({
                "pin_id": str(p.id),
                "artifact_item_id": str(item.id),
                "item_type": item.item_type,
                "content": item.content,
                "citations": item.citations,
                "pinned_at": str(p.pinned_at),
            })
    return result

@router.post("/{session_id}/export")
def export(session_id: str, req: ExportRequest = None, db: DBSession = Depends(get_db)):
    if req is None:
        req = ExportRequest()
    return export_session(db, session_id, req.format, req.include_pins)

@router.post("/{session_id}/deck_builder")
def deck_builder(session_id: str, req: DeckBuilderRequest, db: DBSession = Depends(get_db)):
    try:
        return generate_deck(db, session_id, req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/generate_posts")
def gen_posts(session_id: str, req: ContentSeriesRequest, db: DBSession = Depends(get_db)):
    try:
        return generate_content_series(db, session_id, req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/generate_blogs")
def gen_blogs(session_id: str, req: BlogSeriesRequest, db: DBSession = Depends(get_db)):
    try:
        return generate_blog_series(db, session_id, req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/generate_email")
def gen_email(session_id: str, req: EmailRequest, db: DBSession = Depends(get_db)):
    try:
        return generate_email_sequence(db, session_id, req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/video_pipeline")
def video(session_id: str, req: VideoRequest, db: DBSession = Depends(get_db)):
    try:
        return run_video_pipeline(db, session_id, req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/consolidate_summary")
def consolidate(session_id: str, db: DBSession = Depends(get_db)):
    try:
        return consolidate_summary(db, session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/approval/update_status")
def approval_update(session_id: str, req: ApprovalUpdateRequest, db: DBSession = Depends(get_db)):
    try:
        return update_approval_status(db, session_id, req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/send_webhook")
def webhook(session_id: str, req: WebhookRequest, db: DBSession = Depends(get_db)):
    try:
        return send_webhook(db, session_id, req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from pydantic import BaseModel as PydanticBaseModel
from typing import List, Optional

class ThesisSuggestRequest(PydanticBaseModel):
    source_modules: List[str]

class ImageGenRequest(PydanticBaseModel):
    prompt: str

class AIGenerateRequest(PydanticBaseModel):
    tool: str
    post_text: str
    post_title: Optional[str] = ""

@router.post("/{session_id}/suggest_thesis")
def thesis_suggest(session_id: str, req: ThesisSuggestRequest, db: DBSession = Depends(get_db)):
    try:
        return suggest_thesis(db, session_id, req.source_modules)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/generate_image")
def gen_image(session_id: str, req: ImageGenRequest):
    try:
        from src.backend.services.action_service import generate_post_image
        filename = generate_post_image(req.prompt)
        if filename:
            image_url = f"/static/images/{filename}"
            return {"image_url": image_url, "filename": filename}
        return {"error": "Image generation failed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/ai_generate")
def ai_generate_for_post(session_id: str, req: AIGenerateRequest):
    tool = req.tool.lower()
    title = req.post_title or "Content"
    text = req.post_text

    if tool == "image":
        from src.backend.services.action_service import generate_post_image
        filename = generate_post_image(text[:300])
        if filename:
            return {"tool": "image", "status": "success", "image_url": f"/static/images/{filename}"}
        return {"tool": "image", "status": "error", "message": "Image generation failed"}

    elif tool == "gamma":
        from src.backend.adapters.gamma import generate_presentation, is_configured
        if not is_configured():
            md_content = f"# {title}\n\n{text}"
            return {"tool": "gamma", "status": "manual", "markdown": md_content, "message": "Gamma API key not configured. Copy the markdown below and paste into gamma.app."}
        result = generate_presentation(title, text)
        return {"tool": "gamma", **result}

    elif tool == "heygen":
        from src.backend.adapters.heygen import generate_video, is_configured
        if not is_configured():
            return {"tool": "heygen", "status": "not_configured", "message": "HeyGen API key not configured. Add HEYGEN_API_KEY in Settings."}
        result = generate_video(text[:2000])
        return {"tool": "heygen", **result}

    elif tool == "runway":
        from src.backend.adapters.runway import generate_video, is_configured
        if not is_configured():
            return {"tool": "runway", "status": "not_configured", "message": "Runway API key not configured. Add RUNWAY_API_KEY in Settings."}
        result = generate_video(text[:500])
        return {"tool": "runway", **result}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown AI tool: {tool}")

from src.backend.schemas import ScorePostsRequest, RegeneratePostRequest, RepurposePostRequest
from src.backend.services.action_service import score_posts, regenerate_single_post, repurpose_post, cross_document_insights

@router.post("/{session_id}/score_posts")
def score_posts_endpoint(session_id: str, req: ScorePostsRequest, db: DBSession = Depends(get_db)):
    try:
        scores = score_posts(db, req.posts, req.persona_id)
        return {"scores": scores}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/regenerate_post")
def regenerate_post_endpoint(session_id: str, req: RegeneratePostRequest, db: DBSession = Depends(get_db)):
    try:
        new_post = regenerate_single_post(
            db, session_id, req.post_index, req.posts,
            req.series_thesis, req.platform, req.persona_id
        )
        return new_post
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/repurpose_post")
def repurpose_post_endpoint(session_id: str, req: RepurposePostRequest, db: DBSession = Depends(get_db)):
    try:
        result = repurpose_post(db, session_id, req.post_text, req.post_title, req.persona_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/cross_document_insights")
def cross_doc_insights(session_id: str, db: DBSession = Depends(get_db)):
    try:
        result = cross_document_insights(db, session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
