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

## License

MIT (adjust as needed for your institution).
