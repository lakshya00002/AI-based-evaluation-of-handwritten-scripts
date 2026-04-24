"""Build SubmissionOut with joined grading state."""

from sqlalchemy.orm import Session

from app.models import Result, Submission
from app.schemas import SubmissionOut


def submission_to_out(db: Session, sub: Submission) -> SubmissionOut:
    r = db.query(Result).filter(Result.submission_id == sub.id).first()
    return SubmissionOut(
        id=sub.id,
        assignment_id=sub.assignment_id,
        student_id=sub.student_id,
        file_path=sub.file_path,
        text=sub.text,
        submitted_at=sub.submitted_at,
        grading_complete=r is not None,
        result_score=float(r.score) if r else None,
        result_grade=r.grade if r else None,
    )
