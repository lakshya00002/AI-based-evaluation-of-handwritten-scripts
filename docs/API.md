# API overview

Interactive **OpenAPI 3** documentation is served by FastAPI:

- Swagger UI: `/docs`  
- ReDoc: `/redoc`  
- OpenAPI JSON: `/openapi.json`

Base path for versioned routes: `/api/v1`.

## Auth

- `POST /api/v1/auth/register` — JSON body (`UserCreate`).  
- `POST /api/v1/auth/token` — OAuth2 password form (`username` = email, `password`).  
- Bearer token on protected routes: `Authorization: Bearer <jwt>`.

## Core resources

| Method | Path | Notes |
|--------|------|--------|
| GET | `/assignments` | List assignments |
| POST | `/assignments` | Teacher: create + model answers |
| GET | `/assignments/{id}` | Detail |
| POST | `/submissions/upload` | Multipart: `file`, `assignment_id`, `language_hint`, optional `job_id` |
| POST | `/submissions/batch` | Multiple `files` |
| POST | `/submissions/{id}/evaluate` | JSON: `model_answer_id`, `run_plagiarism` |
| GET | `/submissions/{id}` | OCR text + scores + feedback |
| POST | `/ocr/extract` | Stateless OCR demo (no DB) |
| WS | `/submissions/ws/{job_id}` | Progress messages when `job_id` used on upload |
| POST | `/teacher/scores/{id}/override` | Teacher final score |
| GET | `/teacher/assignments/{id}/submissions` | Cohort view |

## WebSocket message shape

```json
{"stage": "upload", "detail": "Saving file"}
{"stage": "ocr_done", "submission_id": 42}
```
