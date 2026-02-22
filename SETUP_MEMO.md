# StackMind - Setup & Transfer Memo

## What This App Is
StackMind is an AI-powered analysis workbench and Authority Engine. Users upload documents, run structured analysis (Summary, Signals, Claims, Evidence, Canon, etc.), and generate downstream content (social posts, blogs, email sequences, video scripts, decks) tailored to specific audience personas.

## Tech Stack
- **Backend**: Python 3.11 + FastAPI (runs on port 8000)
- **Frontend**: Streamlit (runs on port 5000)
- **Database**: PostgreSQL
- **AI**: OpenAI API (GPT-4o for analysis, DALL-E 3 for images)

## Required Environment Variables
Set these before running:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (e.g. `postgresql://user:pass@host:5432/dbname`) |
| `SESSION_SECRET` | Any random string for session security |
| `OPENAI_API_KEY` | Your OpenAI API key (needed for all AI features) |

## How to Run

### Step 1: Install Python dependencies
```bash
pip install fastapi uvicorn streamlit sqlalchemy psycopg2-binary openai python-multipart pydantic
```

### Step 2: Set up PostgreSQL
Create a PostgreSQL database and set the `DATABASE_URL` environment variable.

### Step 3: Set environment variables
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/stackmind"
export SESSION_SECRET="any-random-string-here"
export OPENAI_API_KEY="sk-your-key-here"
```

### Step 4: Run
```bash
python run.py
```
This starts both the FastAPI backend (port 8000) and Streamlit frontend (port 5000).
Open http://localhost:5000 in your browser.

## What Auto-Creates on First Run
- All database tables
- 2 default libraries (Strategy Documents, Market Research)
- 2 default identities (Strategic Operator, Growth Analyst)
- 8 audience personas (SaaS Founder, VP Marketing, Consultant, PM, Investor, C-Suite, Creator, Sales Leader)
- 1 sample document

## Project Structure
```
src/
  backend/
    main.py              - FastAPI app, startup, seeding
    database.py           - Database connection
    models.py             - All database models
    schemas.py            - API request/response schemas
    services/
      llm_service.py      - OpenAI calls
      file_service.py     - File upload & text extraction
      module_service.py   - Analysis module runner
      action_service.py   - Content generation (posts, blogs, email, video, deck)
      deck_renderer.py    - HTML deck generator
    routes/
      libraries.py        - Library endpoints
      files.py            - File upload endpoints
      identities.py       - Identity endpoints
      sessions.py         - Session & module endpoints
      personas.py         - Audience persona endpoints
      archive.py          - Archive endpoints
      calendar.py         - Content calendar endpoints
    adapters/
      gamma.py            - Gamma deck integration
      heygen.py           - HeyGen video integration
      runway.py           - Runway video integration
      webhook.py          - Webhook sender
  frontend/
    app.py               - Streamlit UI (all pages)
run.py                   - Entry point
```

## For Replit Transfer
If forking to another Replit account:
1. Fork the project
2. Create a new PostgreSQL database (one click)
3. Add SESSION_SECRET in Secrets
4. Enable Replit AI integration (handles OpenAI key automatically)
5. Hit Run

## For GitHub / External Hosting
1. Push code to GitHub
2. Set up PostgreSQL database
3. Set the 3 environment variables listed above
4. Run `python run.py`
