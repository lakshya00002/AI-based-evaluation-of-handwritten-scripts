from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_teacher
from app.ml_integration import evaluate_submission
from app.models import Assignment, Result, Submission, User
from app.schemas import ResultOut

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate/{submission_id}", response_model=ResultOut)
def evaluate(
    submission_id: int,
    force: bool = Query(default=False),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    if not assignment or assignment.created_by != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot evaluate this submission")

    existing = db.query(Result).filter(Result.submission_id == submission.id).first()
    if existing and not force:
        return existing
    if existing and force:
        db.delete(existing)
        db.flush()

    try:
        ml_result = evaluate_submission(
            student_id=submission.student_id,
            assignment_id=assignment.id,
            submission_id=submission.id,
            title=assignment.title,
            description=assignment.description,
            reference_answer=assignment.reference_answer,
            reference_keywords=assignment.reference_keywords,
            reference_concepts=assignment.reference_concepts,
            text=submission.text,
            file_path=submission.file_path,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML evaluation failed: {exc}",
        ) from exc

    ocr_output = ml_result.get("stages", {}).get("ocr_output", {})
    extracted_text_present = bool(ocr_output.get("extracted_text_present"))
    if not extracted_text_present:
        notes = ocr_output.get("notes", [])
        detail = "OCR could not extract text from this submission."
        if notes:
            detail = f"{detail} Details: {' | '.join(str(note) for note in notes[:3])}"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    final_eval = ml_result.get("final_evaluation", {})
    result = Result(
        submission_id=submission.id,
        score=float(final_eval.get("marks_obtained", 0.0)),
        grade=str(final_eval.get("grade", "D")),
        feedback=ml_result.get("feedback", {}),
        created_by=teacher.id,
    )

    db.add(result)
    try:
        db.commit()
    except IntegrityError:
        # Another request may have created this result after our initial check.
        db.rollback()
        existing = db.query(Result).filter(Result.submission_id == submission.id).first()
        if existing:
            return existing
        raise
    db.refresh(result)
    return result
