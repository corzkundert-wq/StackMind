import logging
import time
import os
import zipfile
import io
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from src.backend.database import engine, Base, SessionLocal
from src.backend.models import *
from src.backend.routes.libraries import router as lib_router
from src.backend.routes.files import router as files_router
from src.backend.routes.identities import router as id_router
from src.backend.routes.sessions import router as sess_router
from src.backend.routes.personas import router as persona_router
from src.backend.routes.archive import router as archive_router
from src.backend.routes.calendar import router as calendar_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("stackmind")

app = FastAPI(title="StackMind API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.2f}s)")
    return response

app.include_router(lib_router)
app.include_router(files_router)
app.include_router(id_router)
app.include_router(sess_router)
app.include_router(persona_router)
app.include_router(archive_router)
app.include_router(calendar_router)

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
os.makedirs(os.path.join(static_dir, "decks"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "images"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
def startup():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    seed_defaults()

@app.get("/health")
def health():
    return {"status": "ok", "app": "StackMind"}

@app.get("/download-project")
def download_project():
    workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    skip_dirs = {'__pycache__', '.pythonlibs', '.cache', '.git', '.config', '.local', '.upm', '.nix', 'venv', 'node_modules', 'attached_assets'}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in ['src', 'uploads', 'static']:
            folder_path = os.path.join(workspace, folder)
            if os.path.exists(folder_path):
                for root, dirs, files in os.walk(folder_path):
                    dirs[:] = [d for d in dirs if d not in skip_dirs]
                    for f in files:
                        if f.endswith('.pyc'):
                            continue
                        fp = os.path.join(root, f)
                        arcname = os.path.relpath(fp, workspace)
                        zf.write(fp, arcname)
        for f in ['run.py', 'replit.md', 'SETUP_MEMO.md', '.gitignore', 'pyproject.toml', 'requirements.txt']:
            fp = os.path.join(workspace, f)
            if os.path.exists(fp):
                zf.write(fp, f)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=StackMind-Project.zip"})

@app.get("/integrations/status")
def integrations_status():
    from src.backend.adapters import heygen, runway, gamma
    return {
        "heygen": {"configured": heygen.is_configured(), "name": "HeyGen Video AI"},
        "runway": {"configured": runway.is_configured(), "name": "Runway Video AI"},
        "gamma": {"configured": gamma.is_configured(), "name": "Gamma Presentations"},
    }

@app.post("/integrations/heygen/generate_video")
async def heygen_generate(request: Request):
    from src.backend.adapters.heygen import generate_video
    body = await request.json()
    return generate_video(
        script_text=body.get("script_text", ""),
        avatar_id=body.get("avatar_id"),
        voice_id=body.get("voice_id"),
    )

@app.post("/integrations/heygen/check_status")
async def heygen_status(request: Request):
    from src.backend.adapters.heygen import check_video_status
    body = await request.json()
    return check_video_status(body.get("video_id", ""))

@app.post("/integrations/runway/generate_video")
async def runway_generate(request: Request):
    from src.backend.adapters.runway import generate_video
    body = await request.json()
    return generate_video(
        prompt=body.get("prompt", ""),
        duration=body.get("duration", 5),
    )

@app.post("/integrations/runway/check_status")
async def runway_status(request: Request):
    from src.backend.adapters.runway import check_task_status
    body = await request.json()
    return check_task_status(body.get("task_id", ""))

@app.post("/integrations/gamma/generate")
async def gamma_generate(request: Request):
    from src.backend.adapters.gamma import generate_presentation
    body = await request.json()
    return generate_presentation(
        title=body.get("title", ""),
        markdown_content=body.get("markdown", ""),
        theme=body.get("theme", "professional"),
    )

@app.get("/diagnostics")
def diagnostics():
    db = SessionLocal()
    try:
        logs = db.query(DiagnosticLog).order_by(DiagnosticLog.created_at.desc()).limit(50).all()
        return [{"id": str(l.id), "level": l.level, "module": l.module, "message": l.message, "created_at": str(l.created_at)} for l in logs]
    finally:
        db.close()


def seed_defaults():
    db = SessionLocal()
    try:
        existing_libs = db.query(Library).count()
        if existing_libs == 0:
            lib1 = Library(name="Strategy Documents", description="Strategic planning and analysis documents")
            lib2 = Library(name="Market Research", description="Market research reports and data")
            db.add_all([lib1, lib2])
            db.commit()
            logger.info("Seeded default libraries")

        existing_ids = db.query(Identity).count()
        if existing_ids == 0:
            id1 = Identity(
                name="Strategic Operator",
                definition={
                    "name": "Strategic Operator",
                    "role_context": "Senior strategist evaluating opportunities and risks",
                    "time_horizon": "12m",
                    "risk_bias": "med",
                    "priority_values": ["durability", "leverage", "clarity"],
                    "tone": "analytical",
                    "target_audience": "leadership team",
                },
                is_preset=True,
            )
            id2 = Identity(
                name="Growth Analyst",
                definition={
                    "name": "Growth Analyst",
                    "role_context": "Growth-focused analyst identifying scaling opportunities",
                    "time_horizon": "90d",
                    "risk_bias": "high",
                    "priority_values": ["speed", "leverage"],
                    "tone": "direct",
                    "target_audience": "founders and operators",
                },
                is_preset=True,
            )
            db.add_all([id1, id2])
            db.commit()
            logger.info("Seeded default identities")

        existing_personas = db.query(Persona).count()
        if existing_personas == 0:
            default_personas = [
                Persona(
                    name="SaaS Founder / CEO",
                    description="Early to growth-stage SaaS founder making product, hiring, and fundraising decisions. Needs concise, actionable insights they can act on immediately.",
                    industry="Technology / SaaS",
                    role_title="Founder & CEO",
                    pain_points=["scaling too fast without unit economics", "hiring the right senior team", "competitor differentiation", "fundraising narratives", "churn reduction"],
                    preferred_tone="direct",
                    preferred_cta_style="action-oriented",
                ),
                Persona(
                    name="VP of Marketing",
                    description="Senior marketing leader at a mid-market or enterprise company responsible for pipeline, brand, and content strategy. Values data-backed insights and thought leadership positioning.",
                    industry="B2B Technology",
                    role_title="VP of Marketing",
                    pain_points=["proving marketing ROI", "content fatigue", "attribution across channels", "aligning with sales", "standing out in crowded markets"],
                    preferred_tone="authoritative",
                    preferred_cta_style="strategic",
                ),
                Persona(
                    name="Management Consultant",
                    description="Strategy consultant at a top-tier firm or boutique advisory. Consumes deep analysis to build client recommendations and frameworks. Expects rigorous, well-cited content.",
                    industry="Consulting / Professional Services",
                    role_title="Senior Consultant / Principal",
                    pain_points=["synthesizing large data sets quickly", "building defensible recommendations", "staying current on market shifts", "differentiating advisory value", "client presentation quality"],
                    preferred_tone="analytical",
                    preferred_cta_style="insight-driven",
                ),
                Persona(
                    name="Product Manager",
                    description="Product leader making roadmap and prioritization decisions. Needs market signals, competitive analysis, and user-centric insights to inform product strategy.",
                    industry="Technology",
                    role_title="Senior Product Manager",
                    pain_points=["feature prioritization with limited data", "competitive positioning", "stakeholder alignment", "measuring product-market fit", "roadmap communication"],
                    preferred_tone="conversational",
                    preferred_cta_style="question-driven",
                ),
                Persona(
                    name="Investor / VC Partner",
                    description="Venture capital or private equity investor evaluating deals, market trends, and portfolio strategy. Values pattern recognition, market sizing, and thesis validation.",
                    industry="Venture Capital / Private Equity",
                    role_title="Partner / Principal",
                    pain_points=["deal flow signal vs noise", "thesis validation speed", "portfolio company support", "market timing", "competitive landscape mapping"],
                    preferred_tone="concise",
                    preferred_cta_style="data-backed",
                ),
                Persona(
                    name="Executive / C-Suite",
                    description="Senior executive (COO, CRO, CFO) at a mid-to-large company making strategic decisions. Needs executive summaries, risk assessments, and board-ready insights.",
                    industry="Cross-Industry",
                    role_title="C-Suite Executive",
                    pain_points=["information overload", "decision speed vs accuracy", "board communication", "cross-functional alignment", "market uncertainty"],
                    preferred_tone="executive",
                    preferred_cta_style="decision-oriented",
                ),
                Persona(
                    name="Content Creator / Thought Leader",
                    description="Solo creator, newsletter writer, or LinkedIn influencer building personal brand through expert content. Needs angles, hooks, and repurposable content ideas.",
                    industry="Media / Creator Economy",
                    role_title="Content Creator / Author",
                    pain_points=["content idea generation at scale", "maintaining authenticity", "audience growth plateaus", "monetization strategy", "staying ahead of trends"],
                    preferred_tone="engaging",
                    preferred_cta_style="community-building",
                ),
                Persona(
                    name="Sales Leader / CRO",
                    description="Head of sales or revenue leader responsible for pipeline, deal strategy, and team enablement. Needs competitive intel, objection handling insights, and market positioning.",
                    industry="B2B Sales",
                    role_title="VP Sales / CRO",
                    pain_points=["pipeline predictability", "competitive deal losses", "rep ramp time", "enterprise vs SMB strategy", "sales-marketing alignment"],
                    preferred_tone="persuasive",
                    preferred_cta_style="urgency-driven",
                ),
            ]
            db.add_all(default_personas)
            db.commit()
            logger.info("Seeded default audience personas")

        existing_files = db.query(File).count()
        if existing_files == 0:
            lib = db.query(Library).first()
            if lib:
                import os
                sample_text = """Strategic Planning Framework 2025

Executive Summary:
The market landscape is shifting rapidly with AI-driven automation creating new opportunities for operational efficiency. Companies that adopt modular AI workflows will see 30-40% improvement in decision-making speed.

Key Findings:
1. AI-assisted analysis reduces decision latency by 45%
2. Structured output formats improve team alignment by 60%
3. Citation-backed insights increase stakeholder trust by 35%

Market Trends:
- Enterprise AI adoption growing at 28% CAGR
- Modular workflow tools replacing monolithic platforms
- Data-driven decision making becoming standard practice

Recommendations:
- Invest in structured AI analysis tools
- Build citation and evidence tracking into workflows
- Create reusable knowledge bases from analyzed content
- Implement approval workflows for AI-generated content

Risk Factors:
- Over-reliance on AI without human review
- Data quality issues affecting analysis accuracy
- Regulatory changes in AI-generated content disclosure"""

                sample_path = os.path.join("uploads", "sample_strategy.txt")
                os.makedirs("uploads", exist_ok=True)
                with open(sample_path, "w") as f:
                    f.write(sample_text)

                from src.backend.services.file_service import process_file
                file_record = File(
                    library_id=lib.id,
                    filename="sample_strategy.txt",
                    display_name="Strategic Planning Framework 2025",
                    tags=["strategy", "sample"],
                    status=FileStatus.uploaded,
                )
                db.add(file_record)
                db.commit()
                db.refresh(file_record)
                try:
                    process_file(db, file_record, sample_path)
                    logger.info("Seeded sample file")
                except Exception as e:
                    logger.error(f"Failed to process sample file: {e}")
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
    finally:
        db.close()
