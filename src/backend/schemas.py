from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
import uuid

class InternalCitation(BaseModel):
    file_id: str = ""
    chunk_id: str = ""
    chunk_index: int = 0

class ExternalCitation(BaseModel):
    url: str = ""
    publisher: str = ""
    published_date: str = ""
    tier: int = 1

class LibraryCreate(BaseModel):
    name: str
    description: str = ""

class LibraryOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    class Config:
        from_attributes = True

class FileOut(BaseModel):
    id: str
    library_id: str
    filename: str
    display_name: Optional[str] = None
    uploaded_at: datetime
    tags: list = []
    status: str
    error: Optional[str] = None
    class Config:
        from_attributes = True

class IdentityDefinition(BaseModel):
    name: str = ""
    role_context: str = ""
    time_horizon: str = "90d"
    risk_bias: str = "med"
    priority_values: List[str] = ["clarity"]
    tone: str = "analytical"
    target_audience: Optional[str] = None

class IdentityCreate(BaseModel):
    name: str
    definition: IdentityDefinition
    is_preset: bool = False

class IdentityOut(BaseModel):
    id: str
    name: str
    definition: dict
    created_at: datetime
    is_preset: bool
    class Config:
        from_attributes = True

class IdentityParseRequest(BaseModel):
    free_text: str

class SessionCreate(BaseModel):
    identity_id: str
    library_id: str
    selected_file_ids: List[str] = []
    selection_mode: str = "selected"

class SessionOut(BaseModel):
    id: str
    identity_id: str
    library_id: str
    created_at: datetime
    selection_mode: str
    selected_file_ids: list
    class Config:
        from_attributes = True

class ModuleRunRequest(BaseModel):
    top_k: int = 10
    use_all_chunks: bool = False
    params: dict = {}
    fast: bool = True

class VoteRequest(BaseModel):
    artifact_item_id: str
    vote: str
    note: str = ""

class PinRequest(BaseModel):
    artifact_item_id: str

class ArtifactItemOut(BaseModel):
    id: str
    artifact_id: str
    item_type: str
    content: dict
    confidence: float
    citations: list
    class Config:
        from_attributes = True

class ArtifactOut(BaseModel):
    id: str
    session_id: str
    module_name: str
    created_at: datetime
    params: dict
    items: List[ArtifactItemOut] = []
    class Config:
        from_attributes = True

class SummaryItem(BaseModel):
    summary: str = ""
    key_themes: List[str] = []
    unusual_points: List[str] = []
    open_questions: List[str] = []
    recommended_followups: List[str] = []
    citations: List[dict] = []

class SignalItem(BaseModel):
    insight: str = ""
    why_it_matters: str = ""
    implications: List[str] = []
    confidence: float = 0.0
    citations: List[dict] = []

class ClaimItem(BaseModel):
    claim_text: str = ""
    scope_conditions: str = ""
    predicted_outcome: str = ""
    counterexample_risks: List[str] = []
    confidence: float = 0.0
    citations: List[dict] = []

class EvidenceItem(BaseModel):
    claim_text: str = ""
    supporting_citations: List[dict] = []
    quote_snippet: str = ""
    evidence_strength: str = ""
    citations: List[dict] = []

class RelevanceItem(BaseModel):
    relevance_to: str = ""
    relevance_score: float = 0.0
    implication_action: str = ""
    confidence: float = 0.0
    citations: List[dict] = []

class DurabilityItem(BaseModel):
    durable_principle_candidate: str = ""
    durability_score: float = 0.0
    what_breaks_it: str = ""
    conditions: List[str] = []
    validation_test: str = ""
    citations: List[dict] = []

class LeverageItem(BaseModel):
    leverage_score: float = 0.0
    why: str = ""
    high_leverage_action: str = ""
    second_order_effects: List[str] = []
    citations: List[dict] = []

class CanonItem(BaseModel):
    principle_statement: str = ""
    why_it_matters: str = ""
    applies_when: str = ""
    not_when: str = ""
    operator_checklist: List[str] = []
    anti_patterns: List[str] = []
    examples: List[str] = []
    citations: List[dict] = []
    tags: List[str] = []

class DecisionOption(BaseModel):
    label: str = ""
    description: str = ""
    pros: List[str] = []
    cons: List[str] = []

class DecisionMemoItem(BaseModel):
    situation_summary: str = ""
    key_variables: List[str] = []
    options: List[DecisionOption] = []
    recommendation: str = ""
    risks_mitigations: List[str] = []
    citations: List[dict] = []

class DeckBuilderRequest(BaseModel):
    deck_goal: str = "Pitch"
    audience: str = "CEO"
    slide_count: int = 10
    narrative_style: str = "analytical"
    brand_kit: dict = {}
    source_modules: List[str] = []

class ContentSeriesRequest(BaseModel):
    series_thesis: str = ""
    platform: str = "LinkedIn"
    series_type: str = "series"
    source_modules: List[str] = []

class VideoRequest(BaseModel):
    action: str = "generate_script"
    duration: str = "60s"
    params: dict = {}
    source_modules: List[str] = []

class EmailRequest(BaseModel):
    email_count: int = 3
    source_content: str = ""
    source_modules: List[str] = []

class ApprovalUpdateRequest(BaseModel):
    artifact_id: str
    status: str
    scheduled_for: Optional[str] = None
    channel: Optional[str] = None
    webhook_url: Optional[str] = None

class WebhookRequest(BaseModel):
    artifact_id: str
    webhook_url: str = ""
    channel: str = ""

class BlogSeriesRequest(BaseModel):
    series_thesis: str = ""
    blog_count: int = 3
    target_audience: str = "professionals"
    tone: str = "authoritative"
    source_modules: List[str] = []

class ExportRequest(BaseModel):
    format: str = "markdown"
    include_pins: bool = True

class PersonaCreate(BaseModel):
    name: str
    description: str = ""
    industry: str = ""
    role_title: str = ""
    pain_points: List[str] = []
    preferred_tone: str = "professional"
    preferred_cta_style: str = "direct"

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    role_title: Optional[str] = None
    pain_points: Optional[List[str]] = None
    preferred_tone: Optional[str] = None
    preferred_cta_style: Optional[str] = None

class PersonaOut(BaseModel):
    id: str
    name: str
    description: str
    industry: str
    role_title: str
    pain_points: list
    preferred_tone: str
    preferred_cta_style: str
    created_at: datetime
    class Config:
        from_attributes = True

class ScorePostsRequest(BaseModel):
    posts: List[dict]
    persona_id: Optional[str] = None

class RegeneratePostRequest(BaseModel):
    post_index: int
    posts: List[dict]
    series_thesis: str = ""
    platform: str = "LinkedIn"
    persona_id: Optional[str] = None

class RepurposePostRequest(BaseModel):
    post_text: str
    post_title: str = ""
    persona_id: Optional[str] = None

class SaveContentRequest(BaseModel):
    content_type: str
    title: str
    body: str = ""
    meta: dict = {}
    folder: str = "General"
    session_id: Optional[str] = None

class SavedContentOut(BaseModel):
    id: str
    content_type: str
    title: str
    body: str
    meta: dict
    folder: str
    status: str
    session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class UpdateSavedContentRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    folder: Optional[str] = None
    status: Optional[str] = None
    meta: Optional[dict] = None

class CeoTalkKitRequest(BaseModel):
    identity: str = "CEO / M&A"
    duration: str = "45 minutes"
    audience: str = "ISP Operators"
    output_mode: str = "Generate Full TalkKit"
    include_leverage_pack: bool = True
    source_modules: List[str] = []
    persona_context: Optional[dict] = None
