from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_student, require_teacher
from app.evaluation_bundle import serialize_result_list_row
from app.models import Assignment, Result, Submission, User
from app.schemas import ResultListOut

router = APIRouter(tags=["results"])


def _best_results(rows: list[Result]) -> list[Result]:
    best_by_key: dict[tuple[int, int], Result] = {}
    for row in rows:
        key = (row.submission.assignment_id, row.submission.student_id)
        existing = best_by_key.get(key)
        if existing is None or row.score > existing.score:
            best_by_key[key] = row
    return list(best_by_key.values())


@router.get("/results/student", response_model=list[ResultListOut])
def get_student_results(
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
    each_submission: bool = Query(False, description="If true, return every graded attempt (not only best per assignment)."),
):
    q = (
        db.query(Result)
        .join(Submission, Submission.id == Result.submission_id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(Submission.student_id == student.id)
    )
    if each_submission:
        rows = q.order_by(desc(Submission.submitted_at), desc(Result.id)).all()
    else:
        all_rows = q.all()
        rows = _best_results(all_rows)
    return [serialize_result_list_row(row, row.submission.assignment.title) for row in rows]


@router.get("/results/teacher/{assignment_id}", response_model=list[ResultListOut])
def get_teacher_results(
    assignment_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
    each_submission: bool = Query(
        False,
        description="If true, return every result row (each graded submission); if false, only the best score per student.",
    ),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.created_by != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view results for this assignment")

    q = (
        db.query(Result)
        .join(Submission, Submission.id == Result.submission_id)
        .filter(Submission.assignment_id == assignment_id)
    )
    if each_submission:
        rows = q.order_by(desc(Submission.submitted_at), desc(Result.id)).all()
    else:
        rows = _best_results(q.all())
    return [serialize_result_list_row(row, assignment.title) for row in rows]
