# insightmeet — NLP-Based Meeting Insight Extraction

InsightMeet converts messy, unstructured meeting transcripts into structured, actionable meeting intelligence:
**action items, decisions, issues, suggestions, deadlines, relationships, summaries and grounded Q&A** — with every
insight tied to the exact sentence (and character offsets) it came from. It runs entirely on your CPU, needs no paid
API and no GPU.

## Problem statement

Meeting transcripts are informal and unreliable: inconsistent capitalisation, missing apostrophes, speaker labels,
repeated points, corrections, tentative commitments ("maybe I can try…") and changing deadlines. Keyword matching
produces noise: it assigns tasks to whoever *spoke*, treats suggestions as decisions, and keeps stale deadlines.

## Objectives

- Separate **speaker vs. owner**, **suggestion vs. decision**, **tentative vs. definite**, **original vs. revised
  deadline**, **repeat vs. new information**, **explicit vs. inferred** relationships.
- Never destroy the original text; keep source sentence + position for every insight.
- Mark ambiguity for review instead of inventing an answer.
- Answer questions only from the transcript, and say so when the answer is absent.

## Features

- Paste, `.txt` or `.docx` input with validation and clear errors.
- Preprocessing: sentence segmentation, speaker detection, tokens, lemmas, stop-word handling, contraction repair for
  messy text (analysis view only).
- Representations: Bag of Words, TF-IDF (sparse), LSA (dense) — computed and shown per transcript.
- Six-way sentence classifier (ACTION, DECISION, ISSUE, SUGGESTION, INFORMATION, QUESTION).
- Extraction: actions (owner, deadline history, status, commitment strength, blocked), decisions (explicit / accepted
  suggestion / superseded), issues (component, stated impact, resolved), suggestions (unconfirmed / accepted /
  rejected), deadlines (absolute, relative, event, unresolved), entities, relationships
  (`ASSIGNED_TO`, `DEPENDS_ON`, `BLOCKS`, `AFFECTS`).
- Extractive summary, topics, keyphrases, transcript search, "Ask InsightMeet".
- SQLite meeting history: list, search, open, delete.
- Next.js dashboard with charts, evidence links and a review queue.

## System architecture

```
Next.js (3000) ──HTTP/JSON──▶ FastAPI (8000) ──▶ NLP pipeline ──▶ SQLite (backend/data/insightmeet.db)
 landing · workspace            routes → schemas    preprocessing → classification → entities →
 dashboard · ask · history                          extraction → relationships → summary / QA
```

## NLP methodology

1. **Preprocessing** (`app/nlp/preprocessing.py`): line-level speaker parsing (`Name:`, `[10:02] Name:`,
   `Name (10:02):`), abbreviation-aware sentence splitting, spaCy tokens/lemmas. Each sentence stores `original` and
   exact `start`/`end` offsets into the stored transcript (CRLF normalised once at ingestion). Stop words are removed
   for keyword/overlap work but **kept for classification**, because "will", "should", "not" carry intent.
2. **Representations** (`representation.py`): *Sparse* vectors (BoW, TF-IDF) have one dimension per vocabulary word and
   are mostly zeros; they are interpretable and used for retrieval and the classifier. *Dense* vectors (LSA — truncated
   SVD of TF-IDF) have a few dozen filled dimensions where co-occurring words land close together. Neural sentence
   embeddings are deliberately not included (they need a model download).
3. **Classification** (`classification.py`): TF-IDF (1–2-grams) + Logistic Regression baseline, compared with Naive
   Bayes and Linear SVM, plus a transparent **rule layer** for high-precision cues (e.g. "decided", "can you…?",
   "blocked because"). Each sentence records whether the label came from `rules` or `model`.
4. **Extraction** (`extraction.py`): cue patterns + context windows. Owners come only from first-person commitments, a
   name in the sentence, delegation phrases, or an accepted request. Suggestions become decisions only when another
   speaker clearly agrees; rejections are recorded. Duplicate mentions are merged; same task with two different owners
   is flagged as a contradiction; later conflicting decisions supersede earlier ones.
5. **Dates** (`dates.py`): relative dates are resolved only when a meeting date is supplied; otherwise they stay
   unresolved. Ambiguous numeric dates (`03/04`) are not guessed. A bare weekday means the next occurrence *after* the
   meeting date.
6. **Q&A** (`qa.py`): intent rules over the extracted items, falling back to TF-IDF cosine retrieval over sentences.
   If nothing relevant is found the answer is "Not found in the transcript".

`confidence` on items is a heuristic cue-strength score, **not** a calibrated probability.

## Technology stack

Python 3.10+, FastAPI, Pydantic, spaCy (`en_core_web_sm`), scikit-learn, python-docx, SQLite · Next.js 16, React 19,
TypeScript, Tailwind CSS 4, Recharts, Framer Motion, Lucide.

## Project structure

```
backend/
  app/main.py, config.py, schemas.py, db.py, textio.py
  app/routes/api.py
  app/nlp/ preprocessing, representation, classification, cues, lexicon, dates, entities,
           keyphrases, extraction, relationships, summarization, qa, pipeline
  data/    sentences.csv, handwritten_eval.csv, example_transcript.txt
  models/  metrics.json (+ sentence_classifier.joblib, regenerated)
  scripts/ build_dataset.py, train_classifier.py
  tests/   pytest suite
frontend/  app/ (pages) · components/ · lib/ (API client, types)
```

The original prototype files (`main.py`, `preprocessing.py`, `extraction.py`, `sentence_classifier.py` and two
print-only test scripts) were replaced by the modules above: their ideas (regex cues, TF-IDF + LR, speaker parsing) were
kept and extended, but the originals split text on `.` only (merging unpunctuated chat lines), treated the speaker as
the owner, and trained on 30 sentences. They remain in git history.

## Installation (Windows PowerShell)

```powershell
cd S:\InsightMeet
# backend (the existing .venv already has most packages)
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
python -m spacy download en_core_web_sm

# frontend
cd frontend
npm install
Copy-Item .env.example .env.local   # optional; default API URL is http://localhost:8000
```

## Running

Terminal 1 — backend:

```powershell
cd S:\InsightMeet\backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend:

```powershell
cd S:\InsightMeet\frontend
npm run dev
```

- App: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | backend URL for the frontend |
| `INSIGHTMEET_DB` | `backend/data/insightmeet.db` | SQLite file |
| `INSIGHTMEET_CORS` | `http://localhost:3000,http://127.0.0.1:3000` | allowed origins |
| `INSIGHTMEET_MAX_CHARS` / `INSIGHTMEET_MAX_UPLOAD` | 200000 / 2 MB | input limits |

## API

| Method & path | Purpose |
|---|---|
| `GET /api/health` | status |
| `POST /api/analyze` | `{transcript, title?, meeting_date?}` → full analysis (saved) |
| `POST /api/extract-text` | multipart `file` (.txt/.docx) → text |
| `POST /api/analyze/upload` | multipart file + `title`, `meeting_date` → analysis |
| `GET /api/example-transcript` | built-in example |
| `GET /api/meetings?q=` · `GET/DELETE /api/meetings/{id}` | history |
| `POST /api/meetings/{id}/ask` | `{question}` → grounded answer + evidence |
| `GET /api/meetings/{id}/search?q=` | transcript search |
| `GET /api/model/metrics` | classifier evaluation |

Errors: `422` validation (empty/short text, bad date, corrupt file), `413` too large, `415` unsupported type, `404`
unknown meeting.

## Deploying on Render

The repo includes `render.yaml` (a Render Blueprint) and `backend/Dockerfile`.

1. Push the repo to GitHub, then in Render choose **New → Blueprint** and select it. Render creates two services:
   `insightmeet-api` (Docker, with a 1 GB persistent disk at `/data` holding the SQLite file) and `insightmeet-web`
   (Node).
2. When prompted, leave the two `sync: false` values empty for now and deploy.
3. Copy each service's public URL, then set:
   - on `insightmeet-api`: `INSIGHTMEET_CORS` = the web URL (no trailing slash)
   - on `insightmeet-web`: `NEXT_PUBLIC_API_URL` = the API URL (no trailing slash)
4. Redeploy **both** (the frontend reads `NEXT_PUBLIC_API_URL` at build time).
5. Check `https://<api>/api/health`, then open the web URL and analyze the example transcript.

Notes: a persistent disk needs a paid Render plan (without it history is lost on every deploy); the API uses roughly
200 MB of RAM when measured locally; the app has **no authentication**, so do not store sensitive transcripts on a
public URL.

## Testing

```powershell
cd S:\InsightMeet\backend; pytest                 # 70 tests
cd S:\InsightMeet\frontend; npm run typecheck; npm run build
```

Tests cover preprocessing, dates, dataset leakage, classification, extraction (missing speakers/deadlines, ambiguous
and contradictory assignments, revised deadlines, repeats), Q&A "not found" behaviour, and every API route.

## Model evaluation methodology

`scripts/build_dataset.py` writes `data/sentences.csv`. **The data is synthetic**: hand-written templates per class,
filled with random people/tasks/technologies and some informal noise. The split is **by template** (train / validation
/ test), so no template or identical sentence appears in two splits (enforced by a test). A separate hand-written set
(`handwritten_eval.csv`, 72 sentences) is never used for training. `scripts/train_classifier.py` trains on train,
reports validation/test/hand-written scores for LR, Naive Bayes, SVM and LR + rules, and saves `models/metrics.json`;
the served model is refit on train + validation. Reported: accuracy, macro precision/recall/F1, per-class scores and
confusion matrix.

Measured on the last run (re-run the script to reproduce; nothing is hard-coded): LR alone reached about 71 % accuracy
on the synthetic test split and 81 % on the hand-written set; LR + rules about 96 % and 94 %. **These do not show
real-world accuracy:** the synthetic test is optimistic, the rules were written by the developers who saw the same
template families (so the rules-on-synthetic figure is not independent), and the hand-written set is small and was
labelled by the developers, who also tuned some rules after seeing its errors. No evaluation on independently labelled
real meetings has been done. Please review the hand-written labels yourself.

## Limitations

- Rule-based extraction is English-only and tuned to common phrasings; unusual wording will be missed.
- Run-on speech without punctuation is not split into sentences.
- One task per sentence; coordinated tasks ("fix X and update Y") are not separated.
- Anaphora ("do it") is only linked to an owner via an accepted request; otherwise flagged for review.
- Speaker aliases ("Sriya M" vs "Sriya") are not merged; unlabelled continuation lines inherit the previous speaker.
- spaCy NER on lowercase text is weak; people come mainly from speaker labels and name patterns.
- "next week"/"end of month" are resolved to the end of that period (stated in the deadline note).
- Q&A covers common question types; others fall back to sentence retrieval.

## Future enhancements

Neural sentence embeddings (optional), independently labelled real-meeting evaluation, speaker alias merging,
multi-task sentence splitting, relationship graph view, multilingual support, export to calendar/task tools.
