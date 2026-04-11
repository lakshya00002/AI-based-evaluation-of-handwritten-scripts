# Architecture (text diagram)

## High-level flow

```
┌─────────────┐     HTTPS/JSON      ┌──────────────────────────────────────┐
│ React SPA   │ ◄──────────────────►│ FastAPI (`/api/v1/*`, `/docs`)       │
│ (Vite+TW)   │     WebSocket       │  • Auth (JWT)                        │
└─────────────┘  job progress       │  • Assignments / submissions         │
                                    │  • OCR demo + upload pipeline        │
                                    └───────────────┬──────────────────────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────────────┐
                    │                               │                               │
                    ▼                               ▼                               ▼
            ┌───────────────┐               ┌───────────────┐               ┌───────────────┐
            │ MySQL 8       │               │ File volume   │               │ Sentence-BERT │
            │ Users,        │               │ uploads/      │               │ + KeyBERT     │
            │ Assignments,  │               │               │               │ (CPU/GPU)     │
            │ Submissions,  │               └───────────────┘               └───────────────┘
            │ Scores,       │
            │ Feedback      │
            └───────────────┘
```

## Layered backend layout

| Layer | Responsibility |
|-------|----------------|
| `routes/` | HTTP/WebSocket contracts, dependency injection |
| `controllers/` | Orchestration, transactions, HTTP error mapping |
| `services/` | OCR, preprocessing, NLP, evaluation, plagiarism |
| `models/` | SQLAlchemy ORM ↔ MySQL |
| `schemas/` | Pydantic validation |

## Processing pipeline

1. **Upload** → persist bytes → optional WebSocket `job_id` events  
2. **Preprocess** (OpenCV): denoise → deskew estimate → adaptive binarize → polarity fix  
3. **OCR** (Tesseract; `hin+eng` when `language_hint=hi`)  
4. **Normalize + embed** (Sentence-BERT)  
5. **Score** = weighted semantic similarity + keyword overlap − optional plagiarism penalty  
6. **Feedback** = missing keywords, weak-area heuristics, sentence-level highlight proxy  
7. **Persist** `scores` + `feedback`; teacher may **override** `final_score`

## Explainability

- `explainability_json` stores weighted components, matched/missing keywords, textual rationale.  
- `attention_highlights_json` lists sentences with low keyword overlap (UI “weak regions”), not raw transformer attention maps.

## Scaling notes

- Horizontal scale: stateless API + shared upload store (S3/EFS) + read replicas for MySQL.  
- Heavy OCR/NLP: offload to a worker queue (Celery/RQ) using the same service modules; WebSocket or SSE for progress.
