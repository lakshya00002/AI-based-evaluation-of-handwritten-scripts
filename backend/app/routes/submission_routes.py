"""Upload, OCR, evaluate, batch, WebSocket progress hooks."""

from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload

from app.controllers import submission_controller
from app.controllers.submission_controller import process_upload, submission_to_out
from app.database import get_db
from app.dependencies import get_current_user
from app.models.orm import Score, Submission, User, UserRole
from app.schemas.submission import EvaluateRequest, SubmissionOut
from app.services import ocr_service

router = APIRouter(prefix="/submissions", tags=["submissions"])


class ConnectionManager:
    """Minimal WebSocket fan-out for job progress (OCR / eval)."""

    def __init__(self) -> None:
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(job_id, []).append(ws)

    def disconnect(self, job_id: str, ws: WebSocket) -> None:
        if job_id in self.active:
            self.active[job_id] = [c for c in self.active[job_id] if c is not ws]
            if not self.active[job_id]:
                del self.active[job_id]

    async def broadcast(self, job_id: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for client in self.active.get(job_id, []):
            try:
                await client.send_text(json.dumps(message))
            except Exception:
                dead.append(client)
        for d in dead:
            self.disconnect(job_id, d)


manager = ConnectionManager()


def _load_submission(db: Session, submission_id: int) -> Submission:
    sub = (
        db.query(Submission)
        .options(
            joinedload(Submission.scores).joinedload(Score.feedback),
            joinedload(Submission.scores).joinedload(Score.model_answer),
        )
        .filter(Submission.id == submission_id)
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@router.post("/upload", response_model=SubmissionOut)
async def upload_submission(
    assignment_id: int = Form(...),
    language_hint: str = Form("en"),
    file: UploadFile = File(...),
    job_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionOut:
    if job_id:
        await manager.broadcast(job_id, {"stage": "upload", "detail": "Saving file"})
    sub = await process_upload(db, user, assignment_id, language_hint, file)
    if job_id:
        await manager.broadcast(job_id, {"stage": "ocr_done", "submission_id": sub.id})
    sub_loaded = _load_submission(db, sub.id)
    return submission_to_out(sub_loaded)


@router.post("/batch", response_model=list[SubmissionOut])
async def batch_upload(
    assignment_id: int = Form(...),
    language_hint: str = Form("en"),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SubmissionOut]:
    batch_id = uuid.uuid4().hex
    results: list[SubmissionOut] = []
    for f in files:
        sub = await process_upload(db, user, assignment_id, language_hint, f, batch_id=batch_id)
        sub_loaded = _load_submission(db, sub.id)
        results.append(submission_to_out(sub_loaded))
    return results


@router.post("/{submission_id}/evaluate", response_model=SubmissionOut)
def evaluate(
    submission_id: int,
    body: EvaluateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionOut:
    sub = submission_controller.evaluate_submission(db, user, submission_id, body)
    return submission_to_out(sub)


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionOut:
    sub = (
        db.query(Submission)
        .options(
            joinedload(Submission.scores).joinedload(Score.feedback),
            joinedload(Submission.scores).joinedload(Score.model_answer),
        )
        .filter(Submission.id == submission_id)
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    if sub.student_id != user.id and user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(status_code=403, detail="Not allowed")
    return submission_to_out(sub)


@router.websocket("/ws/{job_id}")
async def ws_progress(job_id: str, websocket: WebSocket) -> None:
    await manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)


ocr_router = APIRouter(prefix="/ocr", tags=["ocr"])


@ocr_router.post("/extract")
async def ocr_extract(
    language_hint: str = Form("en"),
    file: UploadFile = File(...),
) -> dict:
    data = await file.read()
    result = ocr_service.extract_text_auto(data, file.filename or "", language_hint, file.content_type)
    return {"text": result.text, "preprocessing_notes": result.preprocessing_notes}
