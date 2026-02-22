# StackMind

## Overview
StackMind is a click-module-first AI analysis workbench / Authority Engine. Users upload documents, select an identity/perspective, and run structured analysis modules (Summary, Signals, Claims, Evidence, Relevance, Durability, Leverage, Canon Builder, Decision Memo, Market Trends). Outputs are structured JSON with citations. Users can vote, pin, edit, and then use Actions (Posts, Blog Series, Deck Builder, Email Sequence, Video Pipeline, Export, Webhooks) with a full Approval workflow.

## Stack
- **Backend**: Python + FastAPI (port 8000)
- **Frontend**: Streamlit (port 5000, dark theme)
- **Database**: PostgreSQL
- **AI**: OpenAI via Replit AI Integrations (no separate key needed)
- **File Storage**: Local filesystem (`uploads/` directory)

## Project Structure
```
src/
  backend/
    main.py           - FastAPI app with startup, seeding, middleware
    database.py        - SQLAlchemy engine and session
    models.py          - All SQLAlchemy models
    schemas.py         - Pydantic schemas for all endpoints
    services/
      llm_service.py   - LLM calls, embeddings, SVG card generation
      file_service.py  - File upload, text extraction, chunking
      module_service.py - Analysis module runner with prompts
      action_service.py - Deck, posts, blog, email, video, approval, webhook
      deck_renderer.py - HTML deck presentation generator
    routes/
      libraries.py     - Library CRUD
      files.py         - File upload and listing
      identities.py    - Identity CRUD and parsing
      sessions.py      - Sessions, modules, voting, pinning, actions
    adapters/
      gamma.py         - Gamma deck adapter
      heygen.py        - HeyGen video adapter
      runway.py        - Runway video adapter
      webhook.py       - Webhook sender
  frontend/
    app.py            - Streamlit UI with all screens
run.py                - Entry point (starts both FastAPI + Streamlit)
```

## Running
Single command: `python run.py` starts FastAPI on 8000 and Streamlit on 5000.

## Key Features
- 10 analysis modules with structured JSON + citations
- Consolidate All: synthesizes all module results into one executive summary
- Identity system with natural language parsing
- Vote (useful/not/partial), Pin, Edit for all outputs
- **Social Media Posts**: Copy-paste ready with emojis, hashtags, color-coded series numbering, LinkedIn/X share buttons
- **Blog Series**: Full long-form blog posts with SEO keywords, markdown, downloadable
- **Deck Builder**: Visual HTML presentations + Gamma/Canva markdown export
- **Email Sequence**: Ready-to-send email sequences
- **Video Pipeline**: Scripts, scenes, voiceover, SRT captions
- Approval workflow: Draft > Reviewed > Approved > Scheduled > Posted
- Webhook integration for Zapier/Make/n8n
- Export as Markdown/JSON
- Voice/Audio upload with transcription
- AI-generated SVG visual cards for posts (via LLM)
- Diagnostics page for error monitoring

## User Preferences
- Prioritize speed and ready-to-use output
- Posts should be copy-paste ready for social media
- Content should be color-coded and numbered for easy scanning
- Support Gamma/Canva export for presentations
- Authority Engine approach: all content supports building authority

## Recent Changes
- 2026-02-21: Initial MVP build with all core features
- 2026-02-21: Added visual HTML deck renderer with preview/download
- 2026-02-21: Added Blog Series as new content type
- 2026-02-21: Made posts copy-paste ready with emojis, formatting, LinkedIn/X share buttons
- 2026-02-21: Color-coded numbered series layout for posts and blogs
- 2026-02-21: Consolidated Summary module (synthesizes all analysis into one exec summary)
- 2026-02-21: Gamma/Canva markdown export for decks
- 2026-02-21: Fixed image generation (replaced DALL-E with LLM-generated SVG cards)
- 2026-02-21: Reorganized Actions panel: Posts, Blog Series, Deck, Email, Video, Export, Webhook
- 2026-02-21: Fixed SVG visual card display - now renders inline instead of broken URL
- 2026-02-21: Module selector for all Actions (Posts, Blogs, Deck, Email, Video) - choose which analysis findings to base content on
- 2026-02-21: Auto-suggest thesis from selected module findings (AI generates thesis ideas from Claims, Canon, etc.)
- 2026-02-21: Streamlined Posts flow: Select modules → Get thesis suggestions → Choose platform/type → Generate
- 2026-02-21: Real API adapters for HeyGen, Runway, Gamma (with API key support)
- 2026-02-21: Integration status endpoint (/integrations/status)
- 2026-02-22: DALL-E 3 real PNG image generation for posts (replaced SVG cards)
- 2026-02-22: Per-post AI action buttons (DALL-E Image, Gamma PPT, HeyGen Video, Runway Video)
- 2026-02-22: Audience Personas system (DB model, CRUD endpoints, persona page, content injection)
- 2026-02-22: Content Performance Scoring (AI scores 1-100 for engagement, authority, audience fit)
- 2026-02-22: Quick Re-generate per post (fresh content while maintaining series coherence)
- 2026-02-22: One-Click Repurpose Chain (post → blog + email + video script + deck + Twitter thread)
- 2026-02-22: Cross-Document Insights module (patterns, contradictions, story threads across docs)
- 2026-02-22: Regenerate and Repurpose buttons in post UI with expandable repurposed content display
- 2026-02-22: Navigation restored to separate pages: Workbench, Libraries & Upload, Identities, Audience Personas, Actions & Exports, Content Calendar, Archive, Diagnostics
- 2026-02-22: Archive system with SavedContent model, CRUD endpoints, folder/status filtering
- 2026-02-22: Archive page with sub-tabs: All, Posts, Blogs, Decks, Emails, Video Scripts, Exports
- 2026-02-22: Save to Archive buttons on posts, blogs, decks, emails, video scripts
- 2026-02-22: Archive supports: move to folder, update status, download, delete
- 2026-02-22: Persona update endpoint (PATCH) for editing existing personas
- 2026-02-22: Smart Content Calendar with CalendarEntry model, CRUD endpoints, list/monthly views
- 2026-02-22: AI-powered schedule suggestions (platform-specific timing, spacing, color tags)
- 2026-02-22: Calendar entry management: add, update status, delete, color-coded tags
- 2026-02-22: 8 pre-built market-relevant audience personas (SaaS Founder, VP Marketing, Consultant, PM, Investor, C-Suite, Creator, Sales Leader)
- 2026-02-22: Persona context injected into all content generation (posts, blogs, email, video) for audience-tailored output
- 2026-02-22: Persona selector on Workbench session setup — content generated is shaped by chosen audience
- 2026-02-22: Fixed persona UUID serialization (same pattern as archive fix)
