# gita.ai

A multi-acharya Bhagavad-gita commentary aggregator and AI insight engine. Read commentaries from three Vaishnava acharyas side by side, ask them questions in their own voice, and watch them debate each other live.

---

## What it does

- **Browse** — every verse in the Bhagavad-gita (all 18 chapters) with Sanskrit, transliteration, word-for-word translation, and commentaries from three acharyas
- **AI Insights** — per-verse synthesis identifying agreements, divergences, and key themes across commentaries
- **Ask** — chat with the acharyas in a live panel; mention one by name and only they respond; click "Continue" to hear the others
- **Debate** — set a philosophical topic and watch the three acharyas argue it out with each other in real time

---

## Acharyas

| Acharya | Tradition | Emphasis |
|---|---|---|
| A.C. Bhaktivedanta Swami Prabhupada | Gaudiya Vaishnava | Krishna consciousness, bhakti-yoga, devotional service |
| Vishvanatha Chakravarti Thakura | Gaudiya Vaishnava | Rasa, devotional mellows, hidden Sanskrit meanings |
| Baladeva Vidyabhushana | Brahma Vaishnava Sampradaya | Vedanta logic, philosophical precision, Vedic evidence |

Commentaries are scraped from [Vedabase](https://vedabase.io), [Wisdomlib](https://www.wisdomlib.org), and [Bhagavad-gita.org](https://www.bhagavad-gita.org).

---

## Tech stack

- **Backend** — Python, FastAPI, SQLAlchemy 2 (async), SQLite, Anthropic Claude API (Haiku)
- **Scraping** — httpx, BeautifulSoup, tenacity
- **Frontend** — Next.js (App Router), TypeScript, Tailwind CSS
- **AI** — `claude-haiku-4-5` for Q&A, chat, debate turns, and verse insights

---

## Project structure

```
gita-insight-engine/
├── api/
│   ├── main.py          # FastAPI app — all endpoints
│   └── schemas.py       # Pydantic response models
├── analysis/
│   ├── engine.py        # Claude client + verse analysis
│   ├── prompts.py       # Analysis prompt template
│   ├── qa.py            # Q&A and chat logic (acharya personas)
│   └── debate.py        # Debate engine (inter-acharya conversation)
├── db/
│   ├── models.py        # SQLAlchemy models (Verse, Commentary, Insight)
│   ├── session.py       # Async session + init
│   └── crud.py          # DB helpers
├── scrapers/
│   ├── base.py          # Shared HTTP client + retry logic
│   ├── vedabase.py      # Prabhupada commentaries
│   ├── wisdomlib.py     # Vishvanatha commentaries
│   └── bgorg.py         # Baladeva commentaries
├── frontend/            # Next.js app
│   └── app/
│       ├── page.tsx          # Home — chapter list
│       ├── chapter/[n]/      # Chapter view
│       ├── verse/[c]/[v]/    # Verse detail
│       ├── ask/              # Chat with acharyas
│       └── debate/           # Acharya debate
├── ingest.py            # CLI — scrape and save commentaries
├── analyze.py           # CLI — generate AI insights
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone and install Python dependencies

```bash
git clone https://github.com/Aryag1507/gita-insight-engine.git
cd gita-insight-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Add your API key

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Ingest commentaries

```bash
# Scrape all three sources for all 18 chapters
python ingest.py --chapters 1-18 --source all
```

This takes a while (rate-limited to be respectful to source sites). You can run each source separately:

```bash
python ingest.py --chapters 1-18 --source vedabase
python ingest.py --chapters 1-18 --source wisdomlib
python ingest.py --chapters 1-18 --source bgorg
```

### 4. Generate AI insights (optional but recommended)

```bash
python analyze.py --chapters 1-18
```

Cost: ~$0.08–0.10/chapter with Haiku. Full 18 chapters ≈ $1.50.

### 5. Start the backend

```bash
uvicorn api.main:app --reload
# Runs on http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/verses` | List all verses (filter by `?chapter=N`) |
| GET | `/verses/{chapter}/{verse}` | Verse detail with all commentaries and insight |
| GET | `/verses/{chapter}/{verse}/commentaries` | Commentaries only (filter by `?acharya=`) |
| GET | `/verses/{chapter}/{verse}/insight` | AI-generated insight for a verse |
| GET | `/search?q=` | Full-text search across all commentary text |
| POST | `/ask` | One-shot Q&A with all three acharyas |
| POST | `/chat` | Multi-turn conversation (pass `history`); use `acharyas` to filter |
| POST | `/debate` | Run N turns of an inter-acharya debate on a topic |
| GET | `/health` | Health check |

---

## CLI reference

```bash
# Ingest
python ingest.py --chapters 1-18          # all sources
python ingest.py --chapters 2-5 --source vedabase

# Analyze
python analyze.py --chapters 1-18         # all verses
python analyze.py --verse 2.47            # single verse
python analyze.py --chapters 1 --min-acharyas 2  # only verses with 2+ commentaries

# Tests
pytest
```

---

## Notes

- Conversations in the Ask and Debate pages persist in `localStorage` — they survive page navigation and browser refresh. Use "New conversation" to clear.
- The debate engine gives each acharya a **standing philosophical role** (Prabhupada = devotional anchor, Vishvanatha = rasa refiner, Baladeva = logical challenger) so they don't just agree with each other.
- Grouped verses (e.g. BG 2.13–14) are stored under a single `verse_label` matching how the source site presents them.
