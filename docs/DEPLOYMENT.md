# Deployment guide

## Local (Docker Compose)

1. Copy `.env.example` → `.env` and set strong passwords + `SECRET_KEY`.  
2. `docker compose up --build`  
3. API: http://localhost:8000 — Swagger: http://localhost:8000/docs  
4. Seed demo users (optional): install backend deps locally, export `DATABASE_URL` to the compose DB, run `python scripts/seed_demo.py`.

## Backend (container)

- Image: `backend/Dockerfile` (Python 3.12, Tesseract, Hindi+English packs, Poppler for PDF).  
- Required env: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `UPLOAD_DIR`.  
- First cold start downloads SBERT weights (~80MB+); ensure outbound HTTPS.

## Frontend (Vercel / Netlify)

1. Set build command: `cd frontend && npm ci && npm run build`  
2. Publish directory: `frontend/dist`  
3. Environment variable: `VITE_API_URL=https://your-api.example.com` (no trailing slash)  
4. Reconfigure CORS on the API to include the deployed origin.

## Cloud (AWS / GCP sketch)

| Piece | AWS example | GCP example |
|-------|-------------|-------------|
| API | ECS Fargate + ALB | Cloud Run |
| DB | RDS MySQL | Cloud SQL |
| Files | S3 + presigned uploads | GCS |
| Secrets | Secrets Manager | Secret Manager |

Wire `DATABASE_URL` and `UPLOAD_DIR` (or swap local paths for object storage URLs in a future iteration).

## Production checklist

- Replace `Base.metadata.create_all` with **Alembic** migrations.  
- TLS termination at load balancer; `SECRET_KEY` rotation policy.  
- Rate limits on `/auth/token` and upload endpoints.  
- Virus scanning on uploads if accepting arbitrary student files.  
- Backups for MySQL and upload volume.
