import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from src.backend.database import get_db
from src.backend.models import Library
from src.backend.schemas import LibraryCreate

router = APIRouter(prefix="/libraries", tags=["libraries"])

@router.post("")
def create_library(req: LibraryCreate, db: DBSession = Depends(get_db)):
    lib = Library(name=req.name, description=req.description)
    db.add(lib)
    db.commit()
    db.refresh(lib)
    return {"id": str(lib.id), "name": lib.name, "description": lib.description}

@router.get("")
def list_libraries(db: DBSession = Depends(get_db)):
    libs = db.query(Library).order_by(Library.created_at.desc()).all()
    return [{"id": str(l.id), "name": l.name, "description": l.description, "created_at": str(l.created_at)} for l in libs]
