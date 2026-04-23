# Automated Assessment of Handwritten Student Assignments

Production-oriented monorepo combining **computer vision (OCR)**, **sentence-transformer similarity**, and a **FastAPI** backend (async-friendly, OpenAPI-first) with a **React + Tailwind** frontend. MySQL stores users, assignments, submissions, model answers, scores, and feedback.

> The brief also mentioned Flask; this implementation standardizes on **FastAPI** for the API layer to match the requested Docker/OpenAPI/async workflow while keeping the same layered layout (`routes` / `controllers` / `services` / `models`).

## Quick start (Docker)

```bash
cp .env.example .env
# Edit .env: set MYSQL_PASSWORD, SECRET_KEY, etc.

docker compose up --build
```

- API: http://localhost:8000  
- API docs (OpenAPI): http://localhost:8000/docs  
- Frontend dev: `cd frontend && npm install && npm run dev` (proxies `/api` and WebSocket to port 8000)  

## Project layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI app, SQLAlchemy models, OCR/NLP services |
| `frontend/` | React (Vite) UI with charts and drag-drop upload |
| `ml/` | Training/evaluation scripts for grading metrics |
| `sql/schema.sql` | Reference DDL for MySQL |
| `samples/` | Tiny example texts and manifest for tests |
| `docs/` | Architecture, deployment, API notes |

## Environment

- **Tesseract** must be installed on the host (or use the Docker image which installs it).
- First run downloads **Sentence-BERT** weights (`all-MiniLM-L6-v2` by default)—allow network on first start.

## Features

- Image/PDF upload, preprocessing, OCR (pytesseract + OpenCV)
- Weighted scoring: keywords + semantic similarity + optional plagiarism penalty
- Feedback: missing concepts, weak explanation hints, improvement suggestions
- Teacher manual override, batch upload, WebSocket job progress
- English + Hindi text paths (language hint for OCR/normalization)

## NLP-Centric Evaluation Pipeline (Handwritten -> Score)

This repository now includes an explicit end-to-end ML pipeline focused on NLP-based answer evaluation:

1. **Input**: Handwritten answer image/PDF (or typed text for debugging).
2. **OCR Processing**: Extract answer text using OCR engines (`tesseract`, `TrOCR`, `EasyOCR` fallback).
3. **OCR Validation Output**: The extracted text is returned as `stages.ocr_output.extracted_text` for direct inspection.
4. **Error Analysis (OCR vs Ground Truth)**:
   - **CER** (`stages.ocr_error_analysis.cer`)
   - **WER** (`stages.ocr_error_analysis.wer`)
5. **NLP Evaluation**:
   - **BLEU** (`stages.nlp_analysis.bleu_score`) for surface n-gram overlap.
   - **ROUGE-1 / ROUGE-L** (`stages.nlp_analysis.rouge_1_recall`, `stages.nlp_analysis.rouge_l_recall`) for recall-oriented similarity.
   - **Semantic similarity** (`stages.nlp_analysis.semantic_similarity_score`) using Sentence-BERT cosine similarity when available, with a lexical fallback.
6. **Adaptive Scoring**:
   - Combines keyword coverage, BLEU, ROUGE, semantic correctness, concept coverage, structure quality, relevance, and length normalization.
   - Weight map: `stages.adaptive_scoring.weights`
   - Per-metric contribution: `stages.adaptive_scoring.weighted_contributions`
7. **Final Output**:
   - Final normalized score and marks: `final_evaluation`
   - Feedback with strengths, missing keywords, and conceptual gaps.

### Run the pipeline demo

```bash
python -m ml.test_pipeline \
  --input /absolute/path/to/answer_image_or_pdf \
  --ocr-ground-truth "Ground truth transcript for CER/WER" \
  --max-marks 10
```

If you want to test without OCR, pass `--typed-text "..."` and still provide `--ocr-ground-truth` for metric sanity checks.

## License

MIT (adjust as needed for your institution).
