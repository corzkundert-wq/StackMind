from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from src.backend.database import get_db
from src.backend.models import Identity
from src.backend.schemas import IdentityCreate, IdentityParseRequest
from src.backend.services.llm_service import llm_structured_call

router = APIRouter(prefix="/identities", tags=["identities"])

@router.get("")
def list_identities(db: DBSession = Depends(get_db)):
    ids = db.query(Identity).order_by(Identity.created_at.desc()).all()
    return [
        {"id": str(i.id), "name": i.name, "definition": i.definition, "is_preset": i.is_preset, "created_at": str(i.created_at)}
        for i in ids
    ]

@router.post("")
def create_identity(req: IdentityCreate, db: DBSession = Depends(get_db)):
    identity = Identity(
        name=req.name,
        definition=req.definition.model_dump(),
        is_preset=req.is_preset,
    )
    db.add(identity)
    db.commit()
    db.refresh(identity)
    return {"id": str(identity.id), "name": identity.name, "definition": identity.definition}

@router.post("/parse")
def parse_identity(req: IdentityParseRequest, db: DBSession = Depends(get_db)):
    system = """You are StackMind identity parser. Parse the free text into a structured identity.
Return valid JSON with fields: name (string), role_context (string), time_horizon (one of: 30d, 90d, 12m, 24m, 3-5y),
risk_bias (one of: low, med, high), priority_values (array from: durability, leverage, clarity, speed, compliance),
tone (one of: direct, analytical, reflective, persuasive), target_audience (string or null)."""

    result = llm_structured_call(system, f"Parse this identity description:\n\n{req.free_text}")
    return result
