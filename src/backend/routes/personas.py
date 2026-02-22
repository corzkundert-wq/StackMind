from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from src.backend.database import get_db
from src.backend.models import Persona
from src.backend.schemas import PersonaCreate, PersonaUpdate, PersonaOut

router = APIRouter(prefix="/personas", tags=["personas"])

def _persona_to_dict(p):
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description or "",
        "industry": p.industry or "",
        "role_title": p.role_title or "",
        "pain_points": p.pain_points or [],
        "preferred_tone": p.preferred_tone or "",
        "preferred_cta_style": p.preferred_cta_style or "",
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }

@router.get("")
def list_personas(db: DBSession = Depends(get_db)):
    personas = db.query(Persona).order_by(Persona.created_at.desc()).all()
    return [_persona_to_dict(p) for p in personas]

@router.post("")
def create_persona(req: PersonaCreate, db: DBSession = Depends(get_db)):
    persona = Persona(
        name=req.name,
        description=req.description,
        industry=req.industry,
        role_title=req.role_title,
        pain_points=req.pain_points,
        preferred_tone=req.preferred_tone,
        preferred_cta_style=req.preferred_cta_style,
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return _persona_to_dict(persona)

@router.patch("/{persona_id}")
def update_persona(persona_id: str, req: PersonaUpdate, db: DBSession = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    if req.name is not None:
        persona.name = req.name
    if req.description is not None:
        persona.description = req.description
    if req.industry is not None:
        persona.industry = req.industry
    if req.role_title is not None:
        persona.role_title = req.role_title
    if req.pain_points is not None:
        persona.pain_points = req.pain_points
    if req.preferred_tone is not None:
        persona.preferred_tone = req.preferred_tone
    if req.preferred_cta_style is not None:
        persona.preferred_cta_style = req.preferred_cta_style
    db.commit()
    db.refresh(persona)
    return _persona_to_dict(persona)

@router.delete("/{persona_id}")
def delete_persona(persona_id: str, db: DBSession = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    db.delete(persona)
    db.commit()
    return {"status": "deleted"}
