from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, run_startup_migrations
from app.routes.assignment_routes import router as assignment_router
from app.routes.auth_routes import router as auth_router
from app.routes.evaluation_routes import router as evaluation_router
from app.routes.result_routes import router as result_router
from app.routes.submission_routes import router as submission_router

Base.metadata.create_all(bind=engine)
run_startup_migrations()

app = FastAPI(title="AI Assignment Evaluation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(assignment_router)
app.include_router(submission_router)
app.include_router(evaluation_router)
app.include_router(result_router)


@app.get("/")
def health():
    return {"status": "ok"}
