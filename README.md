# DocuLens AI

A Python web app that turns photos, scans, and PDFs of structured documents — invoices, receipts, ID cards, CVs, contracts — into clean, validated JSON.

Drop the file in, pick the document type (or define a custom schema), wait ~10 seconds, get back a structured object you can ship into your accounting system, ATS, CRM, or whatever needs it.

The wow factor: it works on photos of crumpled paper, hand-written notes, multi-page PDFs, and mixed-language documents — because the extraction model **looks at the image directly** instead of relying on OCR text alone.

---

## Why this exists

The standard OCR pipeline — Tesseract → regex → manual review — breaks the moment a document looks different from what you trained on. Add another invoice vendor and you're back to square one.

Vision-LLM extraction (Claude / GPT-4V) flips this: the model reads the layout the way a person does. New layouts work out of the box. You only define **what** you want, not **how** to find it.

This app wraps that pattern into something deployable:

- A clean upload UI
- Predefined schemas for the common document types
- Custom schema builder for the long tail
- Multi-page PDF support
- Forced structured output (no free-form text, no "extracting…" hallucinations)
- An editable JSON view of every result, with provenance per field
- A history of past extractions to compare prompts / schemas

---

## Features

### Inputs
- **JPEG / PNG / WebP** images (any orientation; the model handles rotation and skew)
- **PDF** — single page or multi-page (each page sent as an image to the model)
- **Multi-image upload** — drop several pages of one document at once

### Built-in schemas

| Schema | Fields extracted |
|--------|-----------------|
| **Invoice** | invoice number, dates, vendor, customer, line items, totals, tax, currency |
| **Receipt** | merchant, date, items, totals, payment method |
| **Resume / CV** | name, contact, summary, experience, education, skills, languages |
| **ID Card / Passport** | name, dob, document number, issue / expiry, nationality, sex, type |
| **Contract** | title, parties, effective + expiry dates, key terms, signatures |
| **Business Card** | name, title, company, email, phone, website, address |

### Custom schema mode
Define fields inline: name, type (string / number / date / boolean / list), description. The app generates the JSON Schema, forces Claude to fill it, and stores the result alongside built-in extractions.

### Output guarantees
- Forced via Claude **tool_use** — model is required to call a `submit_extraction` tool with the exact schema
- Pydantic-validated server-side before returning
- "notes" field captures what the model wasn't sure about (page, field, why)

### UI
- Drag-and-drop upload, schema picker, optional notes
- Result page: image gallery (one thumbnail per page) on the left, structured JSON viewer on the right
- Edit any field inline, then **save** (writes back to the database)
- **Download JSON** or **Download CSV** (for tabular schemas like invoice line items)
- History page lists every prior extraction with thumbnails

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Server | **FastAPI** + Uvicorn |
| Templating | **Jinja2** |
| Vision LLM | **Google Gemini** with image input + structured output |
| PDF → image | **pypdfium2** (pure-Python, no system deps) |
| Image handling | **Pillow** |
| Validation | **Pydantic v2** |
| Storage | **SQLite** for metadata; local filesystem for original files + thumbnails |
| Frontend | Vanilla HTML / CSS / JS — no framework |

---

## How it works

```
┌──────────────────────────────────────────────────────────────────────┐
│ User drops a file + picks a schema                                    │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  POST /extract                                                        │
│   • Save the upload                                                   │
│   • If PDF: pypdfium2 rasterises every page at 144 dpi → PNG          │
│   • Save thumbnails (max 2048px on the long edge) for the model       │
│   • Look up the schema → grab its JSON-Schema (from Pydantic)         │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Claude vision call                                                   │
│   messages = [{                                                       │
│     role: "user",                                                     │
│     content: [                                                        │
│       {type: "image", source: ... page 1 ...},                        │
│       {type: "image", source: ... page 2 ...},                        │
│       {type: "text",  text: schema-aware system instructions}         │
│     ]                                                                  │
│   }]                                                                  │
│   tools = [{name: "submit_extraction", input_schema: <json-schema>}]  │
│   tool_choice = {type: "tool", name: "submit_extraction"}             │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Validate with Pydantic, persist, redirect to result page             │
│   • Pydantic.model_validate(claude_output) → catches malformed data   │
│   • Save extracted JSON + notes + token usage                         │
└──────────────────────────────────────────────────────────────────────┘
```

### Why `tool_use` over free-form JSON

Two options work — asking the model to "return JSON" and then parsing, or forcing tool_use with `tool_choice`. We use tool_use because:

1. The model is structurally **prevented** from drifting outside the schema
2. Partial responses are handled cleanly (no "JSON cut off" parsing)
3. We get a single typed payload back, not a free-form text block we have to slice
4. It composes naturally with Pydantic on the server side — same schema in both places

---

## Setup

```bash
cd "Multimodal Document OCR + Extraction"
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
cp .env.example .env             # add GEMINI_API_KEY

# Quick-start
run.bat                          # Windows
# uvicorn app.main:app --reload  # cross-platform
```

Open <http://localhost:8000>.

---

## Folder structure

```
multimodal-document-ocr-extraction/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── run.bat
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI entry + lifespan
│   ├── config.py                # pydantic-settings
│   ├── logger.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pages.py             # GET / and result page
│   │   ├── extract.py           # POST /extract
│   │   └── files.py             # GET /files/{id}/page/{n}
│   ├── core/
│   │   ├── __init__.py
│   │   ├── schemas.py           # All Pydantic schemas + registry
│   │   ├── prompts.py           # System prompts per schema
│   │   ├── pdf.py               # PDF → PIL Image (pypdfium2)
│   │   ├── image.py             # Resize, base64 encode
│   │   ├── extractor.py         # Gemini vision + structured output
│   │   └── storage.py           # SQLite metadata + on-disk files
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html           # Upload + schema picker + history
│   │   └── result.html          # Image gallery + JSON viewer + edit
│   └── static/
│       ├── style.css
│       └── app.js
├── data/                         # Per-extraction files (gitignored)
└── examples/
    └── README.md                 # Where to find sample documents
```

---

## API endpoints

| Method | Path | What |
|--------|------|------|
| GET | `/` | Upload page + recent history |
| POST | `/extract` | Multipart upload → kicks off extraction |
| GET | `/result/{id}` | Result page (HTML) |
| POST | `/result/{id}/save` | Save edited JSON |
| DELETE | `/result/{id}` | Delete an extraction |
| GET | `/files/{id}/page/{n}` | PNG of page N (used by the result page) |
| GET | `/api/result/{id}.json` | Raw extraction JSON |
| GET | `/api/result/{id}.csv` | Tabular line items as CSV (invoices / receipts only) |

---

## Notes on accuracy

- **Tax / amount parsing** — the model is instructed to keep numbers in document-native form (e.g. "1,250.00") AND normalise to floats in a separate field
- **Dates** — normalised to ISO `YYYY-MM-DD` whenever the original is unambiguous
- **Currency** — three-letter ISO code (`USD`, `EUR`, `AZN`) inferred from symbol / context
- **Handwriting** — works for clearly-written notes; messy handwriting still trips it up. The "notes" field flags these
- **Multi-page** — up to 20 pages per request (Claude API limit). The README documents how to chunk longer documents

---

## Roadmap

- [x] Six built-in schemas
- [x] Custom schema builder
- [x] Multi-page PDF input
- [x] Tool-use forced structured output
- [x] Editable JSON viewer with save
- [x] JSON + CSV download
- [x] Extraction history with thumbnails
- [ ] **Per-field confidence** — Claude reports how sure it is about each field
- [ ] **Source bounding boxes** — render where in the image each field was read from
- [ ] **Batch upload** — drop 50 invoices at once, get a CSV
- [ ] **Tesseract / PaddleOCR fallback** — for cost-sensitive deployments, OCR text first then ask Claude to structure it
- [ ] **Donut / LayoutLM comparison** — local open-weights alternative
- [ ] **Webhook on completion** — POST the JSON to a user-specified URL
- [ ] **Auth + multi-user** + per-user history
- [ ] **S3 / R2 storage** for files at scale
- [ ] **Schema fine-tuning** — generate examples to fine-tune a small local model per schema

---

## Why this is a strong portfolio piece

- A real **multimodal AI workflow**, not a wrapper around `Tesseract.extract_text`
- A complete **upload → process → validate → persist → edit → export** loop
- Real use of **Pydantic JSON Schema → Claude tool_use** for guaranteed-shape outputs
- Handles a domain (document AI) that every business needs and most "AI demos" gloss over
- Domain-agnostic — same engine handles invoices, receipts, CVs, ID cards, business cards, contracts
- Honest about limits — README documents Claude API page limits, handwriting accuracy, and the production storage upgrade path

---

## License

MIT.
