import json
import logging
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from src.backend.models import Artifact, ArtifactItem, Pin, Session, Approval, ApprovalStatus, Identity, Persona
from src.backend.services.llm_service import llm_structured_call, llm_structured_call_streaming, generate_image
from src.backend.services.deck_renderer import render_deck_html

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "static", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

logger = logging.getLogger("stackmind")


def suggest_thesis(db: DBSession, session_id: str, source_modules: list) -> dict:
    content = get_session_artifacts_content(db, session_id, source_modules)
    if not content:
        return {"suggestions": [], "error": "No analysis found for selected modules. Run those modules first."}

    identity_ctx = _get_identity_context(db, session_id)
    module_names = ", ".join(source_modules) if source_modules else "all modules"

    system_prompt = f"""You are a strategic content advisor. Based on analysis findings from these modules: {module_names}.
{identity_ctx}
Generate 3-5 thesis suggestions for a content series. Each thesis should be a compelling, specific angle derived from the analysis findings.
Return valid JSON with key "suggestions" containing an array of objects, each with:
- "thesis" (string - the suggested thesis statement, 1-2 sentences)
- "angle" (string - brief description of the angle/approach)
- "source_insight" (string - which finding from the analysis inspired this)
- "recommended_platform" (string - best platform for this thesis: LinkedIn, X/Twitter, etc.)"""

    try:
        result = llm_structured_call(system_prompt, f"Analysis findings:\n{content[:6000]}")
        suggestions = result.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = []
        validated = []
        for s in suggestions:
            if isinstance(s, dict) and s.get("thesis"):
                validated.append({
                    "thesis": str(s.get("thesis", "")),
                    "angle": str(s.get("angle", "")),
                    "source_insight": str(s.get("source_insight", "")),
                    "recommended_platform": str(s.get("recommended_platform", "LinkedIn")),
                })
        return {"suggestions": validated}
    except Exception as e:
        logger.error(f"Thesis suggestion failed: {e}")
        return {"suggestions": [], "error": "Failed to generate suggestions. Try again."}


def get_pinned_content(db: DBSession, session_id: str) -> list:
    pins = db.query(Pin).filter(Pin.session_id == session_id).all()
    items = []
    for p in pins:
        item = db.query(ArtifactItem).filter(ArtifactItem.id == p.artifact_item_id).first()
        if item:
            items.append({
                "id": str(item.id),
                "item_type": item.item_type,
                "content": item.content,
                "citations": item.citations,
            })
    return items


def get_session_artifacts_content(db: DBSession, session_id: str, source_modules: list = None) -> str:
    query = db.query(Artifact).filter(Artifact.session_id == session_id)
    if source_modules:
        query = query.filter(Artifact.module_name.in_(source_modules))
    artifacts = query.all()
    parts = []
    for a in artifacts:
        items = db.query(ArtifactItem).filter(ArtifactItem.artifact_id == a.id).all()
        for item in items:
            parts.append(f"[{a.module_name}] {json.dumps(item.content)}")
    return "\n\n".join(parts)


def get_module_artifacts_by_type(db: DBSession, session_id: str) -> dict:
    artifacts = db.query(Artifact).filter(Artifact.session_id == session_id).all()
    by_module = {}
    for a in artifacts:
        items = db.query(ArtifactItem).filter(ArtifactItem.artifact_id == a.id).all()
        by_module[a.module_name] = [{"content": item.content, "citations": item.citations} for item in items]
    return by_module


def export_session(db: DBSession, session_id: str, format: str = "markdown", include_pins: bool = True) -> dict:
    pinned = get_pinned_content(db, session_id) if include_pins else []
    artifacts = db.query(Artifact).filter(Artifact.session_id == session_id).all()

    if format == "json":
        data = {
            "session_id": session_id,
            "pinned_items": pinned,
            "artifacts": [],
        }
        for a in artifacts:
            items = db.query(ArtifactItem).filter(ArtifactItem.artifact_id == a.id).all()
            data["artifacts"].append({
                "module": a.module_name,
                "items": [{"content": i.content, "citations": i.citations} for i in items],
            })
        return {"format": "json", "content": data}

    md_parts = [f"# StackMind Export\n\nSession: {session_id}\n"]
    if pinned:
        md_parts.append("## Pinned Items\n")
        for p in pinned:
            md_parts.append(f"### {p['item_type']}\n```json\n{json.dumps(p['content'], indent=2)}\n```\n")
    for a in artifacts:
        items = db.query(ArtifactItem).filter(ArtifactItem.artifact_id == a.id).all()
        md_parts.append(f"## {a.module_name.title()}\n")
        for item in items:
            md_parts.append(f"```json\n{json.dumps(item.content, indent=2)}\n```\n")
    return {"format": "markdown", "content": "\n".join(md_parts)}


def generate_deck(db: DBSession, session_id: str, request: dict) -> dict:
    source_modules = request.get("source_modules", [])
    content = get_session_artifacts_content(db, session_id, source_modules=source_modules if source_modules else None)
    if not content.strip():
        return {"error": "No analysis results found for the selected modules. Run some analysis modules first."}
    pinned = get_pinned_content(db, session_id)
    identity_ctx = _get_identity_context(db, session_id)

    system_prompt = f"""You are StackMind deck builder. {identity_ctx}
Create a slide deck outline. Return valid JSON with key "slides" containing an array of objects, each with:
slide_number (int), title (string), body (string), bullets (array of strings), speaker_notes (string), citations (array).
Deck goal: {request.get('deck_goal', 'Pitch')}
Audience: {request.get('audience', 'CEO')}
Slide count: {request.get('slide_count', 10)}
Narrative style: {request.get('narrative_style', 'analytical')}"""

    user_prompt = f"""Source content:
{content}

Pinned items:
{json.dumps(pinned[:10])}

Generate exactly {request.get('slide_count', 10)} slides. Return JSON with "slides" array."""

    result = llm_structured_call(system_prompt, user_prompt)

    artifact = Artifact(
        session_id=session_id,
        module_name="deck_builder",
        params=request,
        raw_output=result,
    )
    db.add(artifact)
    db.flush()

    slides = result.get("slides", [])
    for slide in slides:
        ai = ArtifactItem(
            artifact_id=artifact.id,
            item_type="deck_slide",
            content=slide,
            confidence=0.9,
            citations=slide.get("citations", []),
        )
        db.add(ai)

    approval = Approval(
        session_id=session_id,
        artifact_id=artifact.id,
        status=ApprovalStatus.draft,
    )
    db.add(approval)
    db.commit()

    deck_filename = render_deck_html(slides, title=f"{request.get('deck_goal', 'Deck')} — {request.get('audience', 'Team')}")

    gamma_json = export_deck_for_gamma(slides, title=f"{request.get('deck_goal', 'Deck')} — {request.get('audience', 'Team')}")

    return {"artifact_id": str(artifact.id), "slides": slides, "deck_file": deck_filename, "gamma_json": gamma_json}


def export_deck_for_gamma(slides: list, title: str = "StackMind Deck") -> dict:
    gamma_cards = []
    for s in slides:
        card = {
            "title": s.get("title", ""),
            "content": s.get("body", ""),
            "bullets": s.get("bullets", []),
            "notes": s.get("speaker_notes", ""),
        }
        gamma_cards.append(card)
    return {
        "title": title,
        "cards": gamma_cards,
        "theme": "professional",
        "format": "gamma_compatible",
        "paste_instructions": "Copy the markdown below and paste into Gamma.app or Canva to create your presentation.",
        "markdown": _slides_to_markdown(slides, title),
    }


def _slides_to_markdown(slides: list, title: str) -> str:
    md = f"# {title}\n\n"
    for s in slides:
        md += f"---\n\n## {s.get('title', '')}\n\n"
        md += f"{s.get('body', '')}\n\n"
        for b in s.get("bullets", []):
            md += f"- {b}\n"
        if s.get("speaker_notes"):
            md += f"\n> Speaker Notes: {s['speaker_notes']}\n"
        md += "\n"
    return md


def generate_content_series(db: DBSession, session_id: str, request: dict) -> dict:
    source_modules = request.get("source_modules", [])
    content = get_session_artifacts_content(db, session_id, source_modules=source_modules if source_modules else None)
    if not content.strip():
        return {"error": "No analysis results found for the selected modules. Run some analysis modules first."}
    pinned = get_pinned_content(db, session_id)
    identity_ctx = _get_identity_context(db, session_id)
    platform = request.get('platform', 'LinkedIn')

    persona_ctx = _get_persona_from_request(request)

    system_prompt = f"""You are StackMind content series engine — an Authority Engine that creates ready-to-publish social media content. {identity_ctx}
{persona_ctx}

Create a 6-post content series. Each post must be FULLY READY TO COPY AND PASTE directly into {platform}.
Include appropriate emojis, line breaks, formatting, and hashtag blocks.

Return valid JSON with key "posts" containing an array of 6 objects, each with:
- post_number (int 1-6)
- post_type (one of: hook, proof, story, counterpoint, framework, CTA)
- series_label (string like "Part 1 of 6: The Hook" — use this for visual numbering)
- color_tag (one of: blue, green, orange, purple, red, teal — assign a unique color to each post for visual coding)
- text (string — the FULL post text ready to paste. Include emojis, line breaks using \\n, paragraph spacing. Make it engaging and professional. For {platform}, use the right tone and length.)
- image_prompt (string — a detailed visual description for a social media graphic)
- hashtags (array of 5-8 hashtag strings including #)
- cta (string — clear call to action)
- compliance_note (string — any notes about claims or disclaimers)
- best_time_to_post (string — suggested posting time/day for {platform})
- estimated_engagement (string — expected engagement type: likes, shares, comments)
- citations (array)

Platform: {platform}
Series thesis: {request.get('series_thesis', '')}
Series type: {request.get('series_type', 'series')}"""

    user_prompt = f"""Source content:
{content}

Pinned items:
{json.dumps(pinned[:10])}

Generate exactly 6 posts for the series. Each post text must be COMPLETE and ready to copy-paste into {platform}.
Include emojis, proper spacing/line breaks, and hashtag block at the end.
Return JSON with "posts" array."""

    result = llm_structured_call(system_prompt, user_prompt)

    artifact = Artifact(
        session_id=session_id,
        module_name="content_series",
        params=request,
        raw_output=result,
    )
    db.add(artifact)
    db.flush()

    posts = result.get("posts", [])
    for post in posts:
        ai = ArtifactItem(
            artifact_id=artifact.id,
            item_type="content_post",
            content=post,
            confidence=0.9,
            citations=post.get("citations", []),
        )
        db.add(ai)

    approval = Approval(
        session_id=session_id,
        artifact_id=artifact.id,
        status=ApprovalStatus.draft,
    )
    db.add(approval)
    db.commit()

    return {"artifact_id": str(artifact.id), "posts": posts}


def generate_blog_series(db: DBSession, session_id: str, request: dict) -> dict:
    source_modules = request.get("source_modules", [])
    content = get_session_artifacts_content(db, session_id, source_modules=source_modules if source_modules else None)
    if not content.strip():
        return {"error": "No analysis results found for the selected modules. Run some analysis modules first."}
    pinned = get_pinned_content(db, session_id)
    identity_ctx = _get_identity_context(db, session_id)
    count = request.get("blog_count", 3)

    persona_ctx = _get_persona_from_request(request)

    system_prompt = f"""You are StackMind Blog Series Engine — an Authority Engine for long-form content. {identity_ctx}
{persona_ctx}

Create a {count}-part blog series. Each blog should be COMPLETE and ready to publish.

Return valid JSON with key "blogs" containing an array of {count} objects, each with:
- blog_number (int)
- series_label (string like "Part 1 of {count}: [Title]")
- color_tag (one of: blue, green, orange, purple, red, teal — unique per blog)
- title (string — SEO-optimized headline)
- subtitle (string — engaging subtitle)
- meta_description (string — 160 char SEO meta description)
- seo_keywords (array of 5-8 keyword strings)
- body (string — the COMPLETE blog post in markdown format, 800-1500 words. Include headers, bullet points, bold text, quotes. Make it authoritative and well-structured.)
- key_takeaways (array of 3-5 string takeaways)
- cta (string — call to action at the end)
- internal_links_suggestions (array of strings — topics to link to)
- estimated_read_time (string like "5 min read")
- citations (array)

Series thesis: {request.get('series_thesis', '')}
Target audience: {request.get('target_audience', 'professionals')}
Tone: {request.get('tone', 'authoritative')}"""

    user_prompt = f"""Source content:
{content}

Pinned items:
{json.dumps(pinned[:10])}

Generate exactly {count} complete blog posts. Each must be fully written and ready to publish.
Return JSON with "blogs" array."""

    result = llm_structured_call(system_prompt, user_prompt)

    artifact = Artifact(
        session_id=session_id,
        module_name="blog_series",
        params=request,
        raw_output=result,
    )
    db.add(artifact)
    db.flush()

    blogs = result.get("blogs", [])
    for blog in blogs:
        ai = ArtifactItem(
            artifact_id=artifact.id,
            item_type="blog_post",
            content=blog,
            confidence=0.9,
            citations=blog.get("citations", []),
        )
        db.add(ai)

    approval = Approval(
        session_id=session_id,
        artifact_id=artifact.id,
        status=ApprovalStatus.draft,
    )
    db.add(approval)
    db.commit()

    return {"artifact_id": str(artifact.id), "blogs": blogs}


def generate_email_sequence(db: DBSession, session_id: str, request: dict) -> dict:
    source_modules = request.get("source_modules", [])
    content = get_session_artifacts_content(db, session_id, source_modules=source_modules if source_modules else None)
    if not content.strip():
        return {"error": "No analysis results found for the selected modules. Run some analysis modules first."}
    pinned = get_pinned_content(db, session_id)
    identity_ctx = _get_identity_context(db, session_id)
    count = request.get("email_count", 3)

    persona_ctx = _get_persona_from_request(request)

    system_prompt = f"""You are StackMind email sequence generator. {identity_ctx}
{persona_ctx}
Create an email sequence. Return valid JSON with key "emails" containing an array of {count} objects, each with:
email_number (int), subject (string), preview_text (string), body (string), cta (string), citations (array)."""

    user_prompt = f"""Source content:
{content}

Pinned items:
{json.dumps(pinned[:10])}

Generate exactly {count} emails. Return JSON with "emails" array."""

    result = llm_structured_call(system_prompt, user_prompt)

    artifact = Artifact(
        session_id=session_id,
        module_name="email_sequence",
        params=request,
        raw_output=result,
    )
    db.add(artifact)
    db.flush()

    emails = result.get("emails", [])
    for email in emails:
        ai = ArtifactItem(
            artifact_id=artifact.id,
            item_type="email",
            content=email,
            confidence=0.9,
            citations=email.get("citations", []),
        )
        db.add(ai)

    approval = Approval(
        session_id=session_id,
        artifact_id=artifact.id,
        status=ApprovalStatus.draft,
    )
    db.add(approval)
    db.commit()

    return {"artifact_id": str(artifact.id), "emails": emails}


def run_video_pipeline(db: DBSession, session_id: str, request: dict) -> dict:
    source_modules = request.get("source_modules", [])
    content = get_session_artifacts_content(db, session_id, source_modules=source_modules if source_modules else None)
    if not content.strip():
        return {"error": "No analysis results found for the selected modules. Run some analysis modules first."}
    pinned = get_pinned_content(db, session_id)
    identity_ctx = _get_identity_context(db, session_id)
    action = request.get("action", "generate_script")
    duration = request.get("duration", "60s")

    persona_ctx = _get_persona_from_request(request)

    actions_map = {
        "generate_script": {
            "system": f"""You are StackMind video script writer. {identity_ctx} {persona_ctx}
Return valid JSON with "script" object containing: title (string), duration (string), scenes (array of objects with scene_number, description, dialogue, duration_seconds), total_duration_seconds (int), citations (array).""",
            "item_type": "video_script",
        },
        "generate_scenes": {
            "system": f"""You are StackMind scene planner. {identity_ctx}
Return valid JSON with "scenes" array of objects each with: scene_number (int), visual_description (string), b_roll_prompt (string), duration_seconds (int), transition (string), citations (array).""",
            "item_type": "scene_list",
        },
        "generate_voiceover": {
            "system": f"""You are StackMind voiceover script writer. {identity_ctx}
Return valid JSON with "voiceover" object containing: script_text (string), ssml (string), timing_marks (array of objects with time, text), citations (array).""",
            "item_type": "voiceover_script",
        },
        "generate_srt": {
            "system": f"""You are StackMind SRT caption generator. {identity_ctx}
Return valid JSON with "srt" object containing: srt_content (string - valid SRT format), line_count (int).""",
            "item_type": "srt_captions",
        },
        "render_plan": {
            "system": f"""You are StackMind video render planner. {identity_ctx}
Return valid JSON with "render_plan" object containing: platform (string), settings (object), estimated_duration (string), steps (array of strings), requirements (array of strings).""",
            "item_type": "render_plan",
        },
    }

    config = actions_map.get(action, actions_map["generate_script"])

    user_prompt = f"""Source content:
{content}

Pinned items:
{json.dumps(pinned[:5])}

Duration target: {duration}. Generate the {action} output. Return JSON."""

    result = llm_structured_call(config["system"], user_prompt)

    artifact = Artifact(
        session_id=session_id,
        module_name="video_pipeline",
        params=request,
        raw_output=result,
    )
    db.add(artifact)
    db.flush()

    ai = ArtifactItem(
        artifact_id=artifact.id,
        item_type=config["item_type"],
        content=result,
        confidence=0.9,
        citations=result.get("citations", []),
    )
    db.add(ai)

    approval = Approval(
        session_id=session_id,
        artifact_id=artifact.id,
        status=ApprovalStatus.draft,
    )
    db.add(approval)
    db.commit()

    return {"artifact_id": str(artifact.id), "action": action, "result": result}


def update_approval_status(db: DBSession, session_id: str, request: dict) -> dict:
    artifact_id = request.get("artifact_id")
    new_status = request.get("status")

    approval = db.query(Approval).filter(
        Approval.session_id == session_id,
        Approval.artifact_id == artifact_id,
    ).first()

    if not approval:
        approval = Approval(
            session_id=session_id,
            artifact_id=artifact_id,
            status=ApprovalStatus(new_status),
        )
        db.add(approval)
    else:
        approval.status = ApprovalStatus(new_status)

    if request.get("scheduled_for"):
        try:
            approval.scheduled_for = datetime.fromisoformat(request["scheduled_for"])
        except Exception:
            pass
    if request.get("channel"):
        approval.channel = request["channel"]

    approval.updated_at = datetime.utcnow()

    if new_status == "posted":
        approval.posted_at = datetime.utcnow()

    db.commit()
    return {
        "artifact_id": artifact_id,
        "status": new_status,
        "updated_at": str(approval.updated_at),
    }


def send_webhook(db: DBSession, session_id: str, request: dict) -> dict:
    from src.backend.adapters.webhook import send_webhook_payload
    artifact_id = request.get("artifact_id")
    webhook_url = request.get("webhook_url") or os.environ.get("WEBHOOK_DEFAULT_URL", "")
    channel = request.get("channel", "")

    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        return {"error": "Artifact not found"}

    items = db.query(ArtifactItem).filter(ArtifactItem.artifact_id == artifact_id).all()
    payload = {
        "session_id": session_id,
        "artifact_id": artifact_id,
        "module_name": artifact.module_name,
        "channel": channel,
        "items": [{"content": i.content, "citations": i.citations} for i in items],
        "timestamp": datetime.utcnow().isoformat(),
    }

    result = send_webhook_payload(webhook_url, payload)
    return result


def generate_post_image(prompt: str) -> str:
    try:
        image_bytes = generate_image(prompt)
        if not image_bytes:
            return ""
        filename = f"post_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(IMAGES_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return filename
    except Exception as e:
        logger.error(f"Post image generation failed: {e}")
        return ""


def consolidate_summary(db: DBSession, session_id: str) -> dict:
    modules_data = get_module_artifacts_by_type(db, session_id)
    identity_ctx = _get_identity_context(db, session_id)

    modules_content = ""
    for mod_name, items in modules_data.items():
        if mod_name in ("deck_builder", "content_series", "blog_series", "email_sequence", "video_pipeline"):
            continue
        modules_content += f"\n\n=== {mod_name.upper()} ===\n"
        for item in items:
            modules_content += json.dumps(item["content"], indent=1) + "\n"

    if not modules_content.strip():
        return {"error": "No module results found. Run some analysis modules first (signals, claims, evidence, etc.) before consolidating."}

    system_prompt = f"""You are StackMind Master Summarizer. {identity_ctx}

You are consolidating ALL analysis module results into one unified executive summary.
The user has run various modules (summary, signals, claims, evidence, relevance, durability, leverage, canon, decision_memo, market_trends).

Return valid JSON with key "items" containing an array of exactly one object with:
- executive_summary (string — 2-3 paragraph high-level overview that synthesizes ALL findings)
- top_signals (array of strings — the 3-5 most important signals found)
- key_claims (array of strings — the strongest claims identified)
- evidence_quality (string — overall assessment of evidence strength)
- relevance_verdict (string — how relevant the content is to the identity/role)
- durability_assessment (string — how durable the key principles are)
- leverage_opportunities (array of strings — highest-leverage actions)
- risks_and_gaps (array of strings — key risks and knowledge gaps)
- recommended_actions (array of strings — prioritized next steps)
- confidence_score (float 0-1 — overall confidence in the analysis)
- citations (array)"""

    user_prompt = f"""Here are ALL the analysis results from different modules:
{modules_content}

Synthesize everything into one unified executive summary that connects the dots across all modules.
Return JSON with "items" array containing exactly one comprehensive summary object."""

    result = llm_structured_call(system_prompt, user_prompt)
    return result


def _deduplicate_chunks(chunk_texts: list, max_chunks: int = 10, max_chars_per_chunk: int = 2000) -> list:
    seen_hashes = set()
    unique = []
    for text in chunk_texts:
        text = text[:max_chars_per_chunk]
        import hashlib as _hl
        h = _hl.md5(text[:500].encode()).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique.append(text)
        if len(unique) >= max_chunks:
            break
    return unique


def generate_ceo_talkkit(db: DBSession, session_id: str, request: dict) -> dict:
    source_modules = request.get("source_modules", [])
    content = ""
    if source_modules:
        content = get_session_artifacts_content(db, session_id, source_modules=source_modules)

    session_obj = db.query(Session).filter(Session.id == session_id).first()
    if not session_obj:
        return {"error": "Session not found"}

    from src.backend.models import File as FileModel, Chunk
    import uuid as uuid_mod
    file_ids = session_obj.selected_file_ids or []
    if session_obj.selection_mode == "all" or not file_ids:
        all_files = db.query(FileModel).filter(FileModel.library_id == session_obj.library_id).all()
        file_ids = [str(f.id) for f in all_files]

    all_chunk_texts = []
    for fid in file_ids:
        try:
            fid_uuid = uuid_mod.UUID(str(fid))
        except ValueError:
            fid_uuid = fid
        chunks = db.query(Chunk).filter(Chunk.file_id == fid_uuid).order_by(Chunk.chunk_index).limit(10).all()
        for c in chunks:
            all_chunk_texts.append(c.text)

    if not all_chunk_texts:
        all_files = db.query(FileModel).filter(FileModel.library_id == session_obj.library_id).all()
        for f in all_files:
            if f.raw_text and f.raw_text.strip():
                all_chunk_texts.append(f.raw_text[:2000])
            else:
                chunks = db.query(Chunk).filter(Chunk.file_id == f.id).order_by(Chunk.chunk_index).limit(10).all()
                for c in chunks:
                    all_chunk_texts.append(c.text)

    deduped = _deduplicate_chunks(all_chunk_texts, max_chunks=10, max_chars_per_chunk=2000)
    raw_text = "\n\n---\n\n".join(deduped)

    if not raw_text.strip() and not content.strip():
        return {"error": "No content found. Upload files to your library first."}

    combined_source = raw_text[:12000]
    if content.strip():
        combined_source += f"\n\n=== PRIOR ANALYSIS ===\n{content[:3000]}"

    tk_identity = request.get("identity", "CEO / M&A")
    tk_duration = request.get("duration", "45 minutes")
    tk_audience = request.get("audience", "ISP Operators")
    tk_mode = request.get("output_mode", "Generate Full TalkKit")
    tk_leverage = request.get("include_leverage_pack", True)

    identity_ctx = _get_identity_context(db, session_id)
    persona_ctx = _get_persona_from_request(request)

    identity_overlay = {
        "CEO / M&A": "Focus on deal rationale, strategic value creation, synergy capture, and executive decision framing. Use boardroom-level language.",
        "Operator": "Focus on operational playbooks, execution metrics, team alignment, and ground-level reality. Speak like a practitioner.",
        "Growth Investor": "Focus on growth vectors, TAM expansion, unit economics, and scalable moats. Use investor-grade framing with data hooks.",
    }
    overlay = identity_overlay.get(tk_identity, identity_overlay["CEO / M&A"])

    duration_guidance = {
        "30 minutes": "Tight and punchy. Max 8 topics. Run-of-show: 5 min opening, 18 min core, 5 min Q&A, 2 min close. Audience moment at minute 15.",
        "45 minutes": "Standard keynote. 10 topics. Run-of-show: 5 min opening, 28 min core (3 acts), 8 min Q&A, 4 min close. Audience moments at minutes 15 and 30.",
        "60 minutes": "Full executive session. 12 topics. Run-of-show: 7 min opening, 35 min core (3-4 acts), 12 min Q&A, 6 min close. Audience moments every 15 min.",
        "90 minutes": "Deep-dive session. 12+ topics. Run-of-show: 8 min opening, 50 min core (4-5 acts), 5 min break, 15 min Q&A, 7 min close. Audience moments every 12-15 min.",
        "150 minutes": "Half-day workshop. 12+ topics with depth. Run-of-show: 10 min opening, 55 min Act 1, 10 min break, 45 min Act 2, 10 min break, 15 min Q&A, 5 min close. Audience moments every 10-12 min.",
    }
    dur_guide = duration_guidance.get(tk_duration, duration_guidance["45 minutes"])

    if tk_mode == "Recommend First (show recommended anchor + structure before full generation)":
        system_prompt = f"""You are StackMind CEO TalkKit Engine — a strategic talk preparation system. {identity_ctx}
{persona_ctx}
Identity overlay: {overlay}
Duration: {tk_duration}
Duration structure guidance: {dur_guide}
Audience: {tk_audience}

Analyze the transcript/content and provide ONLY the recommended anchor and structure preview.

Return valid JSON with these keys:
- "recommended_anchor" (object with "core_thesis" string, "why_this_anchor" string explaining why this is the strongest anchor from the content, "confidence" float 0-1)
- "recommended_structure" (object with "acts" array of objects each with "act_number" int, "title" string, "duration_minutes" int, "purpose" string, "fatigue_note" string)
- "top_topics_preview" (array of top 5 topic strings with approximate weight percentage)
- "audience_alignment_note" (string — how well the content maps to {tk_audience})"""

        user_prompt = f"""Analyze this content and recommend the best anchor thesis and talk structure for a {tk_duration} talk to {tk_audience}.

CONTENT:
{combined_source}

Return the recommendation JSON."""

        result = llm_structured_call_streaming(system_prompt, user_prompt, max_tokens=2048, fast=True, use_cache=True)
        result["mode"] = "recommend_first"

        artifact = Artifact(
            session_id=session_id,
            module_name="ceo_talkkit",
            params=request,
            raw_output=result,
        )
        db.add(artifact)
        db.flush()
        ai = ArtifactItem(
            artifact_id=artifact.id,
            item_type="ceo_talkkit_recommendation",
            content=result,
            confidence=0.9,
            citations=[],
        )
        db.add(ai)
        db.commit()
        return {"artifact_id": str(artifact.id), "result": result}

    base_system = f"""You are StackMind CEO TalkKit Engine — a comprehensive strategic talk preparation system. {identity_ctx}
{persona_ctx}
Identity overlay: {overlay}
Duration: {tk_duration}
Duration structure guidance: {dur_guide}
Audience: {tk_audience}"""

    base_user = f"""Generate from this content for a {tk_duration} talk to {tk_audience}.

CONTENT:
{combined_source}

Return valid JSON with ONLY the requested keys."""

    prompt_part1_sys = f"""{base_system}

Return valid JSON with these keys ONLY:

- "emphasis_map" (object with:
    "topics" array of 8-12 objects each with "topic" string, "weight_pct" float (must sum to ~100), "recurring_phrases" array of strings, "conviction_level" string (high/medium/low), "tone_note" string, "top_excerpt" string
)

- "recommended_anchor" (object with:
    "core_thesis" string — one clear thesis sentence,
    "why_this_anchor" string — reasoning,
    "confidence" float 0-1
)

- "recommended_structure" (object with:
    "acts" array of objects each with "act_number" int, "title" string, "duration_minutes" int, "purpose" string, "fatigue_note" string
)

- "messaging_framework" (object with:
    "one_sentence_thesis" string,
    "pillars" array of 3-5 objects each with "pillar_name" string, "insight" string, "tension_addressed" string, "signature_line" string, "supporting_excerpt" string
)"""

    prompt_part2_sys = f"""{base_system}

Return valid JSON with these keys ONLY:

- "run_of_show" (array of objects each with:
    "timestamp" string like "00:00-05:00",
    "segment" string,
    "content_notes" string,
    "speaker_energy" string (high/medium/low),
    "audience_moment" boolean
)

- "slide_skeleton" (array of 12-18 objects each with:
    "slide_number" int,
    "title" string,
    "bullets" array of max 3 strings,
    "speaker_notes" string,
    "is_audience_moment" boolean
)"""

    prompt_part3_sys = f"""{base_system}

Return valid JSON with these keys ONLY:

- "qa_authority_bank" (array of 15 objects each with:
    "question" string,
    "answer_20sec" string — concise 20-second answer,
    "answer_2min" string — detailed 2-minute answer,
    "category" string like "strategic", "operational", "financial", "skeptic"
)"""

    if tk_leverage:
        prompt_part3_sys += """

- "content_leverage_pack" (object with:
    "linkedin_post" string — a full ready-to-paste LinkedIn post based on the talk's core thesis,
    "hook_lines" array of 5 strings — attention-grabbing opening lines,
    "hot_takes" array of 5 strings — bold contrarian statements from the talk,
    "poll_questions" array of 3 strings — engaging poll questions for social media
)"""

    import concurrent.futures
    def _call_part(sys_p, usr_p, tokens):
        return llm_structured_call_streaming(sys_p, usr_p, max_tokens=tokens, fast=True, use_cache=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        f1 = executor.submit(_call_part, prompt_part1_sys, base_user, 4096)
        f2 = executor.submit(_call_part, prompt_part2_sys, base_user, 4096)
        f3 = executor.submit(_call_part, prompt_part3_sys, base_user, 4096)
        r1 = f1.result(timeout=240)
        r2 = f2.result(timeout=240)
        r3 = f3.result(timeout=240)

    result = {}
    for partial in [r1, r2, r3]:
        if not partial.get("error"):
            result.update(partial)
        else:
            logger.warning(f"TalkKit partial call returned error: {partial.get('error')}")
            result.update(partial)
    result["mode"] = "full"

    artifact = Artifact(
        session_id=session_id,
        module_name="ceo_talkkit",
        params=request,
        raw_output=result,
    )
    db.add(artifact)
    db.flush()

    sections = ["emphasis_map", "recommended_anchor", "recommended_structure",
                 "messaging_framework", "run_of_show", "slide_skeleton",
                 "qa_authority_bank"]
    if tk_leverage:
        sections.append("content_leverage_pack")

    for section in sections:
        section_data = result.get(section)
        if section_data:
            ai = ArtifactItem(
                artifact_id=artifact.id,
                item_type=f"ceo_talkkit_{section}",
                content={section: section_data},
                confidence=0.9,
                citations=[],
            )
            db.add(ai)

    approval = Approval(
        session_id=session_id,
        artifact_id=artifact.id,
        status=ApprovalStatus.draft,
    )
    db.add(approval)
    db.commit()

    return {"artifact_id": str(artifact.id), "result": result}


def _get_identity_context(db: DBSession, session_id: str) -> str:
    session_obj = db.query(Session).filter(Session.id == session_id).first()
    if not session_obj:
        return ""
    identity = db.query(Identity).filter(Identity.id == session_obj.identity_id).first()
    if not identity:
        return ""
    d = identity.definition or {}
    return f"Identity: {d.get('name', '')} | Role: {d.get('role_context', '')} | Tone: {d.get('tone', '')}"


def _get_persona_context(db: DBSession, persona_id: str) -> str:
    if not persona_id:
        return ""
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        return ""
    return _format_persona_context_dict({
        "name": persona.name,
        "description": persona.description,
        "role_title": persona.role_title,
        "industry": persona.industry,
        "pain_points": persona.pain_points or [],
        "preferred_tone": persona.preferred_tone,
        "preferred_cta_style": persona.preferred_cta_style,
    })


def _format_persona_context_dict(p: dict) -> str:
    if not p or not p.get("name"):
        return ""
    parts = [f"\nTarget Audience Persona: {p['name']}"]
    if p.get("description"):
        parts.append(f"Description: {p['description']}")
    if p.get("role_title"):
        parts.append(f"Role/Title: {p['role_title']}")
    if p.get("industry"):
        parts.append(f"Industry: {p['industry']}")
    if p.get("pain_points"):
        pp = p["pain_points"] if isinstance(p["pain_points"], list) else [p["pain_points"]]
        parts.append(f"Pain Points: {', '.join(pp)}")
    if p.get("preferred_tone"):
        parts.append(f"Preferred Tone: {p['preferred_tone']}")
    if p.get("preferred_cta_style"):
        parts.append(f"CTA Style: {p['preferred_cta_style']}")
    parts.append("IMPORTANT: Tailor ALL content specifically for this audience persona. Use their language, address their pain points, and match their preferred tone.")
    return "\n".join(parts)


def _get_persona_from_request(request: dict) -> str:
    pc = request.get("persona_context")
    if pc:
        return _format_persona_context_dict(pc)
    return ""


def score_posts(db: DBSession, posts: list, persona_id: str = None) -> list:
    persona_ctx = _get_persona_context(db, persona_id) if persona_id else ""
    posts_text = ""
    for i, p in enumerate(posts):
        posts_text += f"\n--- Post {i+1} ---\n{p.get('text', '')}\nHashtags: {p.get('hashtags', [])}\n"

    system_prompt = f"""You are a content performance analyst. Score each post for social media effectiveness.
{persona_ctx}
Return valid JSON with key "scores" containing an array of objects (one per post), each with:
- "post_index" (int, 0-based)
- "engagement_score" (int 1-100, predicted engagement/virality)
- "authority_score" (int 1-100, how well it builds thought leadership)
- "audience_fit" (int 1-100, alignment with target audience)
- "overall_score" (int 1-100, weighted average)
- "strengths" (array of 2-3 short strings)
- "improvements" (array of 1-2 short improvement suggestions)"""

    try:
        result = llm_structured_call(system_prompt, f"Score these posts:\n{posts_text[:6000]}")
        scores = result.get("scores", [])
        if not isinstance(scores, list):
            return []
        return scores
    except Exception as e:
        logger.error(f"Post scoring failed: {e}")
        return []


def regenerate_single_post(db: DBSession, session_id: str, post_index: int, posts: list,
                           series_thesis: str = "", platform: str = "LinkedIn", persona_id: str = None) -> dict:
    identity_ctx = _get_identity_context(db, session_id)
    persona_ctx = _get_persona_context(db, persona_id) if persona_id else ""
    content = get_session_artifacts_content(db, session_id)

    other_posts = ""
    for i, p in enumerate(posts):
        if i != post_index:
            other_posts += f"\nPost {i+1}: {p.get('text', '')[:200]}...\n"

    system_prompt = f"""You are a content strategist creating social media posts. {identity_ctx}
{persona_ctx}
The user wants to regenerate Post {post_index + 1} from a series. Keep the same series theme but create a FRESH, DIFFERENT angle.
Platform: {platform}
Series thesis: {series_thesis or 'based on analysis'}
Other posts in the series (do NOT duplicate these):
{other_posts}

Return valid JSON with these keys:
- "text" (string, the full post text with emojis)
- "hashtags" (array of 3-5 hashtags)
- "post_type" (string)
- "cta" (string, call to action)
- "best_time_to_post" (string)
- "estimated_engagement" (string)
- "image_prompt" (string, description for visual)"""

    try:
        result = llm_structured_call(system_prompt, f"Create a fresh post based on:\n{content[:4000]}")
        return result
    except Exception as e:
        logger.error(f"Post regeneration failed: {e}")
        return {"error": str(e)}


def repurpose_post(db: DBSession, session_id: str, post_text: str, post_title: str = "", persona_id: str = None) -> dict:
    identity_ctx = _get_identity_context(db, session_id)
    persona_ctx = _get_persona_context(db, persona_id) if persona_id else ""

    system_prompt = f"""You are a content repurposing expert. Take a social media post and transform it into multiple content formats.
{identity_ctx}
{persona_ctx}
Return valid JSON with these keys:
- "blog" (object with "title", "body" as full markdown blog post ~500 words, "seo_keywords" array)
- "email" (object with "subject", "body" as email text, "cta")
- "video_script" (object with "hook", "body", "cta", "duration_estimate")
- "deck_slides" (array of objects each with "title", "bullets" array, max 5 slides)
- "twitter_thread" (array of strings, each max 280 chars, 3-5 tweets)"""

    try:
        result = llm_structured_call(system_prompt, f"Repurpose this post:\nTitle: {post_title}\n\n{post_text}")
        return result
    except Exception as e:
        logger.error(f"Post repurpose failed: {e}")
        return {"error": str(e)}


def cross_document_insights(db: DBSession, session_id: str) -> dict:
    session_obj = db.query(Session).filter(Session.id == session_id).first()
    if not session_obj:
        return {"error": "Session not found"}

    from src.backend.models import File as FileModel, Chunk
    file_ids = session_obj.selected_file_ids or []
    if session_obj.selection_mode == "all" or not file_ids:
        all_files = db.query(FileModel).filter(FileModel.library_id == session_obj.library_id).all()
        file_ids = [str(f.id) for f in all_files]

    if len(file_ids) < 2:
        return {"error": "Cross-document insights require at least 2 documents. Upload more files to your library."}

    file_summaries = []
    for fid in file_ids:
        f = db.query(FileModel).filter(FileModel.id == fid).first()
        if not f:
            continue
        chunks = db.query(Chunk).filter(Chunk.file_id == fid).order_by(Chunk.chunk_index).limit(5).all()
        text = "\n".join([c.text for c in chunks])[:2000]
        file_summaries.append(f"[File: {f.display_name or f.filename}]\n{text}")

    combined = "\n\n---\n\n".join(file_summaries)
    identity_ctx = _get_identity_context(db, session_id)

    system_prompt = f"""You are a cross-document analyst. Analyze multiple documents and find connections, patterns, contradictions, and story threads.
{identity_ctx}
Return valid JSON with these keys:
- "patterns" (array of objects with "pattern", "documents_involved" array, "significance", "confidence" float 0-1)
- "contradictions" (array of objects with "topic", "position_a", "position_b", "documents_involved" array)
- "story_threads" (array of objects with "thread_title", "narrative", "documents_involved" array, "content_angle")
- "unique_angles" (array of objects with "angle", "why_unique", "recommended_format" like post/blog/deck)
- "summary" (string, executive summary of cross-document analysis)"""

    try:
        result = llm_structured_call(system_prompt, f"Analyze these documents for cross-cutting insights:\n{combined[:8000]}")
        return result
    except Exception as e:
        logger.error(f"Cross-document insights failed: {e}")
        return {"error": str(e)}
