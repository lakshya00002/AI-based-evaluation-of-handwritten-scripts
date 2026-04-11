"""Submission upload, OCR, evaluation, teacher override."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models.orm import (
    Assignment,
    Feedback,
    ModelAnswer,
    Score,
    Submission,
    SubmissionStatus,
    User,
    UserRole,
)
from app.schemas.submission import EvaluateRequest, FeedbackOut, OCRResult, ScoreOut, SubmissionOut, TeacherOverrideBody
from app.services import evaluation_service, plagiarism_service
from app.services import ocr_service


async def save_upload(file: UploadFile, dest_dir: Path) -> tuple[str, str, bytes]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename or 'upload'}"
    path = dest_dir / safe_name
    data = await file.read()
    settings = get_settings()
    max_b = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_b:
        raise HTTPException(status_code=413, detail="File too large")
    path.write_bytes(data)
    return str(path), file.content_type or "application/octet-stream", data


async def process_upload(
    db: Session,
    user: User,
    assignment_id: int,
    language_hint: str,
    file: UploadFile,
    batch_id: Optional[str] = None,
) -> Submission:
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    settings = get_settings()
    path_str, mime, data = await save_upload(file, Path(settings.upload_dir))

    sub = Submission(
        assignment_id=assignment_id,
        student_id=user.id,
        original_filename=file.filename,
        stored_path=path_str,
        mime_type=mime,
        language_hint=language_hint,
        status=SubmissionStatus.uploaded,
        batch_id=batch_id,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    try:
        ocr: OCRResult = ocr_service.extract_text_auto(data, file.filename or "", language_hint, mime)
        sub.extracted_text = ocr.text
        sub.status = SubmissionStatus.ocr_done
    except Exception as e:
        sub.status = SubmissionStatus.failed
        sub.extracted_text = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OCR failed: {e!s}",
        ) from e

    db.commit()
    db.refresh(sub)
    return sub


def evaluate_submission(db: Session, user: User, submission_id: int, body: EvaluateRequest) -> Submission:
    sub = (
        db.query(Submission)
        .options(joinedload(Submission.scores).joinedload(Score.feedback))
        .filter(Submission.id == submission_id)
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.student_id != user.id and user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(status_code=403, detail="Not allowed")
    if not sub.extracted_text:
        raise HTTPException(status_code=400, detail="No OCR text; run upload/OCR first")

    model = db.query(ModelAnswer).filter(ModelAnswer.id == body.model_answer_id).first()
    if not model or model.assignment_id != sub.assignment_id:
        raise HTTPException(status_code=400, detail="Invalid model_answer_id for this assignment")

    assignment = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
    assert assignment is not None

    plag_sim: Optional[float] = None
    if body.run_plagiarism:
        peer = plagiarism_service.max_similarity_to_cohort(db, sub.extracted_text, sub.assignment_id, sub.id)
        if peer:
            other_id, plag_sim = peer
            if plag_sim > 0.92:
                plagiarism_service.record_flag(
                    db, sub.id, other_id, plag_sim, note="High embedding similarity to peer submission"
                )

    auto, sem, k_score, explain = evaluation_service.compute_scores(
        sub.extracted_text,
        model,
        assignment.max_score,
        plagiarism_similarity=plag_sim,
    )
    fb_dict = evaluation_service.build_feedback(
        sub.extracted_text, model.reference_text, explain, sem, k_score
    )

    score = (
        db.query(Score)
        .filter(Score.submission_id == sub.id, Score.model_answer_id == model.id)
        .first()
    )
    explain_json = json.loads(explain.model_dump_json())

    if score:
        score.auto_score = auto
        score.semantic_similarity = Decimal(str(round(sem, 6)))
        score.keyword_score = Decimal(str(round(k_score, 6)))
        score.plagiarism_score = Decimal(str(round(plag_sim or 0.0, 6))) if plag_sim is not None else None
        score.explainability_json = explain_json
        if score.final_score is None:
            score.final_score = auto
        db.query(Feedback).filter(Feedback.score_id == score.id).delete()
    else:
        score = Score(
            submission_id=sub.id,
            model_answer_id=model.id,
            auto_score=auto,
            final_score=auto,
            semantic_similarity=Decimal(str(round(sem, 6))),
            keyword_score=Decimal(str(round(k_score, 6))),
            plagiarism_score=Decimal(str(round(plag_sim or 0.0, 6))) if plag_sim is not None else None,
            explainability_json=explain_json,
        )
        db.add(score)
        db.commit()
        db.refresh(score)

    fb = Feedback(
        score_id=score.id,
        summary=fb_dict["summary"],
        missing_concepts_json=fb_dict["missing_concepts"],
        weak_areas_json=fb_dict["weak_areas"],
        suggestions_json=fb_dict["suggestions"],
        attention_highlights_json=fb_dict["attention_highlights"],
    )
    db.add(fb)
    sub.status = SubmissionStatus.evaluated
    db.commit()

    return (
        db.query(Submission)
        .options(
            joinedload(Submission.scores).joinedload(Score.feedback),
            joinedload(Submission.scores).joinedload(Score.model_answer),
        )
        .filter(Submission.id == sub.id)
        .first()
    )


def teacher_override_score(db: Session, teacher: User, score_id: int, body: TeacherOverrideBody) -> Score:
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    score.final_score = body.final_score
    score.graded_by_teacher_id = teacher.id
    if body.note and score.explainability_json:
        score.explainability_json = {**score.explainability_json, "teacher_note": body.note}
    elif body.note:
        score.explainability_json = {"teacher_note": body.note}
    db.commit()
    db.refresh(score)
    return score


def submission_to_out(sub: Submission) -> SubmissionOut:
    scores_out = []
    for sc in sub.scores:
        fbo = None
        if sc.feedback:
            fbo = FeedbackOut(
                summary=sc.feedback.summary,
                missing_concepts=sc.feedback.missing_concepts_json or [],
                weak_areas=sc.feedback.weak_areas_json or [],
                suggestions=sc.feedback.suggestions_json or [],
                attention_highlights=sc.feedback.attention_highlights_json or [],
            )
        scores_out.append(
            ScoreOut(
                id=sc.id,
                auto_score=sc.auto_score,
                final_score=sc.final_score,
                semantic_similarity=sc.semantic_similarity,
                keyword_score=sc.keyword_score,
                plagiarism_score=sc.plagiarism_score,
                explainability=sc.explainability_json,
                model_answer_id=sc.model_answer_id,
                question_key=sc.model_answer.question_key if sc.model_answer else None,
                feedback=fbo,
            )
        )
    return SubmissionOut(
        id=sub.id,
        assignment_id=sub.assignment_id,
        student_id=sub.student_id,
        original_filename=sub.original_filename,
        status=sub.status.value,
        extracted_text=sub.extracted_text,
        language_hint=sub.language_hint,
        batch_id=sub.batch_id,
        created_at=sub.created_at,
        scores=scores_out,
    )
