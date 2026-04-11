"""
FastAPI entrypoint: OpenAPI/Swagger at `/docs`, modular routers, CORS, DB bootstrap.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routes.assignment_routes import router as assignment_router
from app.routes.auth_routes import router as auth_router
from app.routes.submission_routes import ocr_router, router as submission_router
from app.routes.teacher_routes import router as teacher_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create tables on startup (use Alembic in production migrations)."""
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(
    title="Handwritten Assignment Assessment API",
    description="OCR + Sentence-BERT grading with feedback and teacher override.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(assignment_router, prefix=api_prefix)
app.include_router(submission_router, prefix=api_prefix)
app.include_router(teacher_router, prefix=api_prefix)
app.include_router(ocr_router, prefix=api_prefix)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
