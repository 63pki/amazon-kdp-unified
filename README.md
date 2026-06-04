# KDP Unified

**The complete Amazon KDP publishing tool** — merged from 28 open-source repositories into one cohesive platform.

From niche research to published book, all in one place.

---

## What's Inside

| Module | What it does | Source repos |
|--------|-------------|--------------|
| `core/research/` | Keyword mining, BSR→sales model, niche scoring, competitor tracking, trending discovery | kdp-scout ⭐, niche-analyzer-pro, leinguyenpei, wesleyscholl |
| `core/content/` | AI book writing: outline → draft → adversarial edit → evaluate → compile | autonovel, youngReader, kindle-book-agency, duchangyu, kdp-gpt |
| `core/format/` | Markdown/DOCX → EPUB3, PDF paperback, hardcover, large print | book-formatter ⭐, nikmcfly, vpuna, epub-normalizer |
| `core/cover/` | AI cover generation + PIL gradient + typography | autonovel, sabbonzo, authorclaw |
| `core/publish/` | Playwright single-book + CSV bulk publisher (13 markets) | sabbonzo, auto-kdp ⭐, youngReader |
| `core/audiobook/` | Chapter → voiced audiobook pipeline | autonovel, authorclaw |
| `core/marketing/` | Launch orchestrator, AMS ads, blog post, release calendar | authorclaw, fracabu |
| `extensions/kdp_xray_helper/` | Chrome extension: bulk-edit KDP X-Ray entities with AI | Silicon-Federation |
| `data/categories/` | Complete KDP category hierarchy (666 categories) | wmh-kdp-categories |
| `docs/references/` | Cover specs, formatting rules, platform guides, trim sizes | arturseo, duchangyu, nikmcfly |

---

## Quick Start

### 1. Install dependencies

```bash
# Python
pip install -r requirements.txt
playwright install chromium

# Node.js (for bulk publish / X-Ray extension)
npm install
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys
# Edit config.yaml with your book defaults
```

### 3. Run

```bash
# Research a niche
python cli.py research keywords "cozy mystery"
python cli.py research niche "cozy mystery"

# Write a book (full 8-agent pipeline)
python cli.py write agency "cozy mystery set in a bookshop"

# Format your manuscript
python cli.py format all manuscript.md

# Generate a cover
python cli.py cover generate

# Generate KDP metadata
python cli.py metadata generate

# Publish to KDP
python cli.py publish single       # single book (Playwright)
python cli.py publish bulk books.csv  # bulk from CSV

# Full end-to-end pipeline
python cli.py pipeline full "cozy mystery set in a bookshop"
```

---

## Module Details

### Research (`core/research/`)
Powered by **rxpelle/kdp-scout** — the most complete open-source KDP research tool.

```bash
python cli.py research keywords "cozy mystery"      # mine autocomplete
python cli.py research niche "cozy mystery"         # opportunity score
python cli.py research competitors B08XYZ1234       # track by ASIN
python cli.py research bsr 45000                    # estimate daily sales
python cli.py research trending                     # discover niches
```

Key features:
- Amazon autocomplete mining with a-z suffix expansion
- BSR → daily/monthly sales estimation (power-law model, calibrated)
- Semantic keyword clustering via Claude API
- Competitor BSR tracking over time
- Reverse ASIN via DataForSEO (optional)
- Cron-ready automation for daily snapshots

### Content Writing (`core/content/`)
Three writing modes:

**1. Agency mode** (recommended) — 8-agent parallel DAG from `kindle-book-agency`:
```
Niche Researcher → Ghostwriter + Cover Designer + Marketing ← parallel
                → Developmental Editor
                → [N parallel chapter writers]
                → Proofreader + Formatter ← parallel
                → Kindle Compiler → .docx
```

**2. Pipeline mode** — autonomous novel loop from `autonovel`:
```
seed → gen_world → gen_characters → gen_outline → draft_chapter ×N
     → adversarial_edit → evaluate → apply_cuts → gen_revision → typeset
```

**3. Agent mode** — multi-agent series from `youngReader`:
```
BookPlanningAgent → ContentGenerationAgent → ConsistencyAgent → SeriesCoordinator
```

### Formatting (`core/format/`)
Based on **rxpelle/book-formatter** — replaces Vellum ($250) and Atticus ($150).

- EPUB3 — clean, validated, KDP Kindle ready
- PDF Paperback — correct trim, gutters, running headers
- PDF Hardcover — adjusted for case laminate
- PDF Large Print — 16pt body, wider margins
- All KDP trim sizes: 5×8, 5.5×8.5, 6×9, 7×10, 8×10, 8.5×11
- Lua filters: scene breaks, heading promotion
- EPUB normalizer: dedup pages, fix metadata, validate structure

### Publishing (`core/publish/`)

**Single book** (Playwright — sabbonzo):
```bash
python cli.py publish single
```
Automates full 3-step KDP wizard: Details → Content → Pricing across 10+ markets.

**Bulk CSV** (Puppeteer — auto-kdp):
```bash
python cli.py publish bulk books.csv
```
Define 100s of books in a CSV. Supports: create, update, publish, unpublish, archive, assign-isbn, scrape. 13 marketplaces.

---

## Project Structure

```
kdp_unified/
├── cli.py                    ← Master CLI entry point
├── config.yaml               ← All configuration in one file
├── requirements.txt          ← Python deps
├── package.json              ← Node.js deps (bulk publish + X-Ray)
├── .env.example              ← API keys template
│
├── core/
│   ├── research/             ← kdp-scout (keyword mining, BSR model, niche scoring)
│   │   └── collectors/       ← autocomplete, BSR, semantic, trending, DataForSEO
│   ├── content/
│   │   ├── pipeline/         ← autonovel (outline, draft, edit, evaluate)
│   │   └── agents/           ← youngReader + kindle-book-agency
│   │       └── prompts/      ← Agent system prompts (.md files)
│   ├── format/
│   │   ├── generators/       ← EPUB, PDF paperback, PDF hardcover
│   │   ├── parsers/          ← Markdown, DOCX
│   │   ├── templates/        ← CSS + LaTeX templates
│   │   └── filters/          ← Lua filters
│   ├── cover/                ← AI + PIL cover generation
│   ├── publish/
│   │   └── actions/          ← auto-kdp TypeScript actions
│   ├── audiobook/            ← autonovel audiobook pipeline
│   └── marketing/
│       └── agents/           ← fracabu 3-agent marketing pipeline
│
├── data/
│   └── categories/           ← wmh KDP category hierarchy (666 categories)
│
├── extensions/
│   └── kdp_xray_helper/      ← Chrome extension (X-Ray bulk editor)
│
└── docs/
    └── references/           ← Cover specs, trim sizes, platform guides
```

---

## Source Repositories (28 total)

| # | Repo | Module |
|---|------|--------|
| 1 | rxpelle/book-formatter ⭐ | `core/format/` base |
| 2 | rxpelle/kdp-scout ⭐ | `core/research/` base |
| 3 | NousResearch/autonovel | `core/content/pipeline/`, `core/audiobook/` |
| 4 | Ckokoski/authorclaw | `core/marketing/`, `core/cover/` |
| 5 | cbdmaul/youngReader | `core/content/agents/`, `core/publish/` |
| 6 | Harshil-Jani/kindle-book-agency | `core/content/` orchestrator |
| 7 | AHamza786/niche-analyzer-pro | `core/research/` dashboard |
| 8 | Tanner-Eischen/PublishingStrategist | `core/research/` API |
| 9 | fracabu/claude-kdp-agents | `core/marketing/agents/` |
| 10 | Silicon-Federation/KDP-X-Ray-Helper | `extensions/kdp_xray_helper/` |
| 11 | sabbonzo/kdp-autopublish | `core/publish/`, `core/cover/` |
| 12 | ekr0/auto-kdp ⭐ | `core/publish/actions/` |
| 13 | wmh/kdp-categories | `data/categories/` |
| 14 | duchangyu/best-selling-book-writer | `core/content/` metadata |
| 15 | nikmcfly/kindle-book-skill | `core/format/` templates |
| 16 | vpuna/markdown-to-book | `core/format/filters/` |
| 17 | jonatasolmartins/epub-normalizer | `core/format/normalize_epub.py` |
| 18 | leinguyenpei/kdp-publishing-system | `core/research/` NLTK extractor |
| 19 | wesleyscholl/book-generator | `core/research/` market scripts |
| 20 | arturseo/ebook-publishing-skill | `docs/references/` |
| 21 | yegor256/kdpcover | `core/cover/` LaTeX |
| 22 | shenzhuxi/amazon-kdp-keywords | `core/research/` keyword organizer |
| 23 | victorpreston/amazon_kdp_upload_automation | `core/publish/` |
| 24 | BrahimAkar/Amazon-KDP-Automater | `core/publish/` |
| 25 | b7011343/kdp-gpt | `core/content/` simple GPT pipeline |
| 26 | AndrewMyrman/Markdown2EBook | `core/format/` browser-based |
| 27 | Ricswell/ai-master-ebook-converter | `core/format/` validation |
| 28 | zoyth/kdp-book-generator | `core/format/` TypeScript pipeline |

---

## License

MIT. Individual modules inherit their original licenses — see each source repo.
