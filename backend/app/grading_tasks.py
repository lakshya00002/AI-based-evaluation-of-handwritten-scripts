"""Background ML grading after a submission row is committed (keeps HTTP fast)."""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.evaluation_bundle import bundle_evaluation
from app.ml_integration import evaluate_submission
from app.models import Assignment, Result, Submission

logger = logging.getLogger(__name__)


def _persist_failed_result(db: Session, submission_id: int, message: str) -> None:
    if db.query(Result).filter(Result.submission_id == submission_id).first():
        return
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    assignment = (
        db.query(Assignment).filter(Assignment.id == sub.assignment_id).first() if sub else None
    )
    if not sub or not assignment:
        return
    feedback = {
        "_evaluation_incomplete": True,
        "summary_feedback": {},
        "message": message[:2000],
    }
    row = Result(
        submission_id=sub.id,
        score=0.0,
        grade="D",
        feedback=feedback,
        created_by=assignment.created_by,
    )
    db.add(row)
    db.commit()


def run_grading_for_submission(submission_id: int) -> None:
    db: Session = SessionLocal()
    try:
        sub = db.query(Submission).filter(Submission.id == submission_id).first()
        if not sub:
            return
        if db.query(Result).filter(Result.submission_id == submission_id).first():
            return

        assignment = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
        if not assignment:
            logger.warning("grading: assignment missing for submission %s", submission_id)
            return

        try:
            ml_result = evaluate_submission(
                student_id=sub.student_id,
                assignment_id=assignment.id,
                submission_id=sub.id,
                title=assignment.title,
                description=assignment.description,
                reference_answer=assignment.reference_answer,
                reference_keywords=assignment.reference_keywords,
                reference_concepts=assignment.reference_concepts,
                text=sub.text,
                file_path=sub.file_path,
            )
        except Exception as exc:
            logger.exception("grading: evaluate_submission failed for %s", submission_id)
            db.rollback()
            _persist_failed_result(db, submission_id, f"Evaluation failed: {exc}")
            return

        ocr_output = ml_result.get("stages", {}).get("ocr_output", {})
        if not ocr_output.get("extracted_text_present"):
            notes = ocr_output.get("notes", [])
            detail = "OCR could not extract text from this submission."
            if notes:
                detail = f"{detail} Details: {' | '.join(str(note) for note in notes[:3])}"
            db.rollback()
            _persist_failed_result(db, submission_id, detail)
            return

        final_eval = ml_result.get("final_evaluation", {})
        result = Result(
            submission_id=sub.id,
            score=float(final_eval.get("marks_obtained", 0.0)),
            grade=str(final_eval.get("grade", "D")),
            feedback=bundle_evaluation(ml_result),
            created_by=assignment.created_by,
        )
        db.add(result)
        db.commit()
    except Exception:
        logger.exception("grading: unexpected error for submission %s", submission_id)
        db.rollback()
        try:
            if not db.query(Result).filter(Result.submission_id == submission_id).first():
                _persist_failed_result(
                    db,
                    submission_id,
                    "Grading failed unexpectedly. Try re-evaluation from the teacher view.",
                )
        except Exception:
            db.rollback()
    finally:
        db.close()
