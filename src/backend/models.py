import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.backend.database import Base
import enum

class FileStatus(str, enum.Enum):
    uploaded = "uploaded"
    extracted = "extracted"
    chunked = "chunked"
    embedded = "embedded"
    failed = "failed"

class VoteType(str, enum.Enum):
    useful = "useful"
    not_useful = "not"
    partial = "partial"

class ApprovalStatus(str, enum.Enum):
    draft = "draft"
    reviewed = "reviewed"
    approved = "approved"
    scheduled = "scheduled"
    posted = "posted"

class Library(Base):
    __tablename__ = "libraries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    files = relationship("File", back_populates="library", cascade="all, delete-orphan")

class File(Base):
    __tablename__ = "files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    library_id = Column(UUID(as_uuid=True), ForeignKey("libraries.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    display_name = Column(String(500))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    tags = Column(JSONB, default=list)
    raw_text = Column(Text, default="")
    status = Column(SAEnum(FileStatus), default=FileStatus.uploaded)
    error = Column(Text)
    library = relationship("Library", back_populates="files")
    chunks = relationship("Chunk", back_populates="file", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    chunk_metadata = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    file = relationship("File", back_populates="chunks")

class Identity(Base):
    __tablename__ = "identities"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    definition = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_preset = Column(Boolean, default=False)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_id = Column(UUID(as_uuid=True), ForeignKey("identities.id"), nullable=False)
    library_id = Column(UUID(as_uuid=True), ForeignKey("libraries.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    selection_mode = Column(Text, default="selected")
    selected_file_ids = Column(JSONB, default=list)
    identity = relationship("Identity")
    library = relationship("Library")
    artifacts = relationship("Artifact", back_populates="session", cascade="all, delete-orphan")
    pins = relationship("Pin", back_populates="session", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="session", cascade="all, delete-orphan")

class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    module_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    params = Column(JSONB, default=dict)
    raw_output = Column(JSONB, default=dict)
    session = relationship("Session", back_populates="artifacts")
    items = relationship("ArtifactItem", back_populates="artifact", cascade="all, delete-orphan")

class ArtifactItem(Base):
    __tablename__ = "artifact_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False)
    item_type = Column(String(100), nullable=False)
    content = Column(JSONB, nullable=False)
    confidence = Column(Float, default=0.0)
    citations = Column(JSONB, default=list)
    artifact = relationship("Artifact", back_populates="items")

class Vote(Base):
    __tablename__ = "votes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    artifact_item_id = Column(UUID(as_uuid=True), ForeignKey("artifact_items.id"), nullable=False)
    vote = Column(SAEnum(VoteType), nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="votes")

class Pin(Base):
    __tablename__ = "pins"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    artifact_item_id = Column(UUID(as_uuid=True), ForeignKey("artifact_items.id"), nullable=False)
    pinned_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="pins")
    artifact_item = relationship("ArtifactItem")

class Approval(Base):
    __tablename__ = "approvals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False)
    status = Column(SAEnum(ApprovalStatus), default=ApprovalStatus.draft)
    scheduled_for = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    channel = Column(Text, nullable=True)
    meta = Column(JSONB, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExternalSource(Base):
    __tablename__ = "external_sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier = Column(Integer, nullable=False)
    title = Column(Text)
    publisher = Column(Text)
    url = Column(Text)
    published_date = Column(DateTime, nullable=True)
    snippet = Column(Text)
    credibility_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExternalCluster(Base):
    __tablename__ = "external_clusters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    theme = Column(Text)
    alignment_score = Column(Float, default=0.0)
    tier1_count = Column(Integer, default=0)
    tier2_count = Column(Integer, default=0)
    citations = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

class Persona(Base):
    __tablename__ = "personas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    industry = Column(String(255), default="")
    role_title = Column(String(255), default="")
    pain_points = Column(JSONB, default=list)
    preferred_tone = Column(String(100), default="professional")
    preferred_cta_style = Column(String(100), default="direct")
    created_at = Column(DateTime, default=datetime.utcnow)

class ContentType(str, enum.Enum):
    post = "post"
    blog = "blog"
    deck = "deck"
    email = "email"
    video_script = "video_script"
    twitter_thread = "twitter_thread"
    export = "export"

class SavedContent(Base):
    __tablename__ = "saved_content"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    content_type = Column(SAEnum(ContentType), nullable=False)
    title = Column(String(500), nullable=False, default="Untitled")
    body = Column(Text, default="")
    meta = Column(JSONB, default=dict)
    folder = Column(String(255), default="General")
    status = Column(String(50), default="saved")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CalendarEntry(Base):
    __tablename__ = "calendar_entries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), default="post")
    scheduled_date = Column(String(20), nullable=False)
    scheduled_time = Column(String(10), default="09:00")
    platform = Column(String(100), default="")
    status = Column(String(50), default="planned")
    notes = Column(Text, default="")
    content_preview = Column(Text, default="")
    color = Column(String(20), default="blue")
    meta = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DiagnosticLog(Base):
    __tablename__ = "diagnostic_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String(20), default="error")
    module = Column(String(100))
    message = Column(Text)
    details = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
