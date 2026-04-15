from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_student, require_teacher
from app.models import Assignment, Result, Submission, User
from app.schemas import ResultListOut

router = APIRouter(tags=["results"])


def _extract_ocr_text(feedback: dict) -> str | None:
    return (
        feedback.get("stages", {})
        .get("ocr_output", {})
        .get("extracted_text")
    )


def _serialize_result_row(row: Result, assignment_title: str) -> dict:
    return {
        "id": row.id,
        "submission_id": row.submission_id,
        "assignment_id": row.submission.assignment_id,
        "assignment_title": assignment_title,
        "student_id": row.submission.student_id,
        "score": row.score,
        "grade": row.grade,
        "feedback": row.feedback,
        "ocr_extracted_text": _extract_ocr_text(row.feedback or {}),
        "created_by": row.created_by,
    }


def _best_results(rows: list[Result]) -> list[Result]:
    best_by_key: dict[tuple[int, int], Result] = {}
    for row in rows:
        key = (row.submission.assignment_id, row.submission.student_id)
        existing = best_by_key.get(key)
        if existing is None or row.score > existing.score:
            best_by_key[key] = row
    return list(best_by_key.values())


@router.get("/results/student", response_model=list[ResultListOut])
def get_student_results(student: User = Depends(require_student), db: Session = Depends(get_db)):
    rows = (
        db.query(Result)
        .join(Submission, Submission.id == Result.submission_id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(Submission.student_id == student.id)
        .all()
    )
    filtered_rows = _best_results(rows)
    return [_serialize_result_row(row, row.submission.assignment.title) for row in filtered_rows]


@router.get("/results/teacher/{assignment_id}", response_model=list[ResultListOut])
def get_teacher_results(assignment_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.created_by != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view results for this assignment")

    rows = (
        db.query(Result)
        .join(Submission, Submission.id == Result.submission_id)
        .filter(Submission.assignment_id == assignment_id)
        .all()
    )
    filtered_rows = _best_results(rows)
    return [_serialize_result_row(row, assignment.title) for row in filtered_rows]
