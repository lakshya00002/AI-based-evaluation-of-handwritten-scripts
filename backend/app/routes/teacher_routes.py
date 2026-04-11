"""Teacher manual score override and cohort view."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.controllers import submission_controller
from app.database import get_db
from app.dependencies import get_current_teacher
from app.models.orm import Score, Submission, User
from app.schemas.submission import SubmissionOut, TeacherOverrideBody

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.post("/scores/{score_id}/override")
def override_score(
    score_id: int,
    body: TeacherOverrideBody,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
) -> dict:
    submission_controller.teacher_override_score(db, teacher, score_id, body)
    return {"ok": True, "score_id": score_id}


@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionOut])
def list_submissions_for_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
) -> list[SubmissionOut]:
    rows = (
        db.query(Submission)
        .options(
            joinedload(Submission.scores).joinedload(Score.feedback),
            joinedload(Submission.scores).joinedload(Score.model_answer),
        )
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.id.desc())
        .all()
    )
    return [submission_controller.submission_to_out(s) for s in rows]
