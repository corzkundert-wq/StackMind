import logging
from sqlalchemy.orm import Session as DBSession
from src.backend.models import Artifact, ArtifactItem, Chunk, File, Session, Identity
from src.backend.services.llm_service import llm_structured_call, get_embeddings, cosine_similarity, web_search_market_data

logger = logging.getLogger("stackmind")


def get_relevant_chunks(db: DBSession, session_obj: Session, module_name: str, top_k: int = 10, use_all: bool = False) -> list:
    file_ids = session_obj.selected_file_ids or []
    if session_obj.selection_mode == "all" or not file_ids:
        from src.backend.models import File as FileModel
        all_files = db.query(FileModel).filter(FileModel.library_id == session_obj.library_id).all()
        file_ids = [f.id for f in all_files]
    if not file_ids:
        return []
    chunks = db.query(Chunk).filter(Chunk.file_id.in_(file_ids)).order_by(Chunk.chunk_index).all()
    if use_all or len(chunks) <= top_k:
        return chunks
    query_text = f"Analysis for {module_name} module"
    query_emb = get_embeddings([query_text])[0]
    scored = []
    for c in chunks:
        emb = (c.chunk_metadata or {}).get("embedding")
        if emb:
            score = cosine_similarity(query_emb, emb)
            scored.append((score, c))
        else:
            scored.append((0.0, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def build_context(chunks: list) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[Chunk {c.chunk_index} | File: {c.file_id}]\n{c.text}")
    return "\n\n---\n\n".join(parts)


def build_identity_context(db: DBSession, session_obj: Session) -> str:
    identity = db.query(Identity).filter(Identity.id == session_obj.identity_id).first()
    if not identity:
        return ""
    d = identity.definition or {}
    return f"""Identity: {d.get('name', '')}
Role: {d.get('role_context', '')}
Time Horizon: {d.get('time_horizon', '')}
Risk Bias: {d.get('risk_bias', '')}
Priorities: {', '.join(d.get('priority_values', []))}
Tone: {d.get('tone', '')}
Audience: {d.get('target_audience', 'general')}"""


def make_citations(chunks: list) -> list:
    return [{"file_id": str(c.file_id), "chunk_id": str(c.id), "chunk_index": c.chunk_index} for c in chunks[:5]]


def run_module(db: DBSession, session_id: str, module_name: str, top_k: int = 10, use_all: bool = False, params: dict = None) -> dict:
    session_obj = db.query(Session).filter(Session.id == session_id).first()
    if not session_obj:
        raise ValueError("Session not found")

    chunks = get_relevant_chunks(db, session_obj, module_name, top_k, use_all)
    if not chunks:
        raise ValueError("No content found. Please select files with processed content.")

    context = build_context(chunks)
    identity_ctx = build_identity_context(db, session_obj)
    citations_hint = make_citations(chunks)

    prompts = MODULE_PROMPTS.get(module_name)
    if not prompts:
        raise ValueError(f"Unknown module: {module_name}")

    system_prompt = prompts["system"].format(identity_context=identity_ctx)

    extra_context = ""
    if module_name == "market_trends":
        identity = db.query(Identity).filter(Identity.id == session_obj.identity_id).first()
        search_topic = ""
        if identity and identity.definition:
            d = identity.definition
            search_topic = f"{d.get('role_context', '')} {d.get('target_audience', '')}"
        if not search_topic.strip():
            search_topic = context[:500]
        market_data = web_search_market_data(search_topic)
        if market_data:
            extra_context = f"\n\n=== MARKET RESEARCH DATA ===\n{market_data}\n=== END MARKET RESEARCH ===\n"

    user_prompt = prompts["user"].format(context=context + extra_context, citations_hint=str(citations_hint), **(params or {}))

    result = llm_structured_call(system_prompt, user_prompt)

    artifact = Artifact(
        session_id=session_obj.id,
        module_name=module_name,
        params=params or {},
        raw_output=result,
    )
    db.add(artifact)
    db.flush()

    items_data = result.get("items", [result])
    if not isinstance(items_data, list):
        items_data = [items_data]

    created_items = []
    for item_data in items_data:
        item_citations = item_data.pop("citations", citations_hint) if isinstance(item_data, dict) else citations_hint
        confidence = item_data.pop("confidence", 0.8) if isinstance(item_data, dict) else 0.8
        ai = ArtifactItem(
            artifact_id=artifact.id,
            item_type=module_name,
            content=item_data if isinstance(item_data, dict) else {"data": item_data},
            confidence=float(confidence) if confidence else 0.8,
            citations=item_citations if isinstance(item_citations, list) else [],
        )
        db.add(ai)
        created_items.append(ai)

    db.commit()
    db.refresh(artifact)
    return {
        "artifact_id": str(artifact.id),
        "module_name": module_name,
        "items": [
            {
                "id": str(i.id),
                "item_type": i.item_type,
                "content": i.content,
                "confidence": i.confidence,
                "citations": i.citations,
            }
            for i in created_items
        ],
    }


MODULE_PROMPTS = {
    "summary": {
        "system": """You are StackMind, an analytical AI. {identity_context}
Return valid JSON with key "items" containing an array of exactly one object with fields:
summary (string), key_themes (array of strings), unusual_points (array of strings),
open_questions (array of strings), recommended_followups (array of strings), citations (array of objects with file_id, chunk_id, chunk_index).""",
        "user": """Analyze the following content and produce a structured summary.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array.""",
    },
    "signals": {
        "system": """You are StackMind, a signal detection AI. {identity_context}
Return valid JSON with key "items" containing an array of objects, each with fields:
insight (string), why_it_matters (string), implications (array of strings), confidence (float 0-1), citations (array).""",
        "user": """Identify key signals from this content.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array (3-5 signals).""",
    },
    "claims": {
        "system": """You are StackMind, a claims analyzer. {identity_context}
Return valid JSON with key "items" containing an array of objects, each with:
claim_text (string), scope_conditions (string), predicted_outcome (string), counterexample_risks (array of strings), confidence (float 0-1), citations (array).""",
        "user": """Extract key claims from this content.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array (3-5 claims).""",
    },
    "evidence": {
        "system": """You are StackMind, an evidence evaluator. {identity_context}
Return valid JSON with key "items" containing an array of objects, each with:
claim_text (string), supporting_citations (array), quote_snippet (string), evidence_strength (string: strong/moderate/weak), citations (array).""",
        "user": """Evaluate evidence in this content.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array.""",
    },
    "relevance": {
        "system": """You are StackMind, a relevance scorer. {identity_context}
Return valid JSON with key "items" containing an array of objects, each with:
relevance_to (string), relevance_score (float 0-5), implication_action (string), confidence (float 0-1), citations (array).""",
        "user": """Score the relevance of this content to the identity/project.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array.""",
    },
    "durability": {
        "system": """You are StackMind, a durability analyst. {identity_context}
Return valid JSON with key "items" containing an array of objects, each with:
durable_principle_candidate (string), durability_score (float 0-5), what_breaks_it (string), conditions (array of strings), validation_test (string), citations (array).""",
        "user": """Assess the durability of principles in this content.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array.""",
    },
    "leverage": {
        "system": """You are StackMind, a leverage analyst. {identity_context}
Return valid JSON with key "items" containing an array of objects, each with:
leverage_score (float 0-5), why (string), high_leverage_action (string), second_order_effects (array of strings), citations (array).""",
        "user": """Identify high-leverage opportunities in this content.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array.""",
    },
    "canon": {
        "system": """You are StackMind, a canon builder. {identity_context}
Return valid JSON with key "items" containing an array of objects, each with:
principle_statement (string), why_it_matters (string), applies_when (string), not_when (string), operator_checklist (array of strings), anti_patterns (array of strings), examples (array of strings), citations (array), tags (array of strings).""",
        "user": """Build canon entries from this content.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array (1-3 canon entries).""",
    },
    "decision_memo": {
        "system": """You are StackMind, a decision memo generator. {identity_context}
Return valid JSON with key "items" containing an array with exactly one object with:
situation_summary (string), key_variables (array of strings), options (array of objects with label, description, pros, cons), recommendation (string), risks_mitigations (array of strings), citations (array).""",
        "user": """Generate a decision memo from this content.

CONTENT:
{context}

Available citations: {citations_hint}

Return JSON with "items" array.""",
    },
    "market_trends": {
        "system": """You are StackMind, a market trends analyst with access to current market research data. {identity_context}
You combine the user's uploaded document content with real-time market intelligence to provide actionable market analysis.
Return valid JSON with key "items" containing an array of objects, each with:
trend_clusters (array of strings - key market trends identified), tier1_evidence (array of objects with source, finding, relevance), tier2_evidence (array of objects with source, finding, relevance), alignment_score (float 0-5 - how well the content aligns with market trends), relevance_to_identity (string), market_position (string - where the user stands relative to trends), competitive_landscape (string), implications_actions (array of strings - actionable next steps), citations (array).""",
        "user": """Analyze market trends by combining the uploaded content with current market research data.

UPLOADED CONTENT & MARKET RESEARCH:
{context}

Available citations: {citations_hint}

Provide a comprehensive market analysis that combines insights from the uploaded documents with real market data. Include current trends, competitive positioning, and actionable recommendations.
Return JSON with "items" array.""",
    },
}
