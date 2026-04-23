from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.dependencies import require_student, require_teacher
from app.evaluation_bundle import bundle_evaluation
from app.ml_integration import evaluate_submission
from app.models import Assignment, Result, Submission, User
from app.schemas import SubmissionOut

router = APIRouter(tags=["submissions"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _delete_submission_row(db: Session, submission_id: int) -> None:
    db.query(Result).filter(Result.submission_id == submission_id).delete(synchronize_session=False)
    row = db.query(Submission).filter(Submission.id == submission_id).first()
    if row:
        db.delete(row)
    db.commit()


def _unlink_stored_upload(file_path: str | None) -> None:
    if not file_path:
        return
    rel = Path(file_path)
    candidates = []
    if rel.is_absolute() and rel.exists():
        candidates.append(rel)
    else:
        candidates.extend([BACKEND_ROOT / rel, PROJECT_ROOT / rel, UPLOAD_DIR / rel.name])
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file():
            resolved.unlink()
            return


@router.get("/submissions/mine", response_model=list[SubmissionOut])
def list_my_submissions(student: User = Depends(require_student), db: Session = Depends(get_db)):
    return (
        db.query(Submission)
        .filter(Submission.student_id == student.id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )


@router.delete("/submissions/mine/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_submissions_for_assignment(
    assignment_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    if assignment.due_date:
        due_utc = assignment.due_date
        if due_utc.tzinfo is None:
            due_utc = due_utc.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > due_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment due date has passed. You cannot delete this submission.",
            )

    rows = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id, Submission.student_id == student.id)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No submission found for this assignment")

    for sub in rows:
        db.query(Result).filter(Result.submission_id == sub.id).delete()
        _unlink_stored_upload(sub.file_path)
        db.delete(sub)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/submit", response_model=SubmissionOut)
def submit_assignment(
    assignment_id: int = Form(...),
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    if assignment.due_date:
        due_utc = assignment.due_date
        if due_utc.tzinfo is None:
            due_utc = due_utc.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > due_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment due date has passed. Submission is closed.",
            )

    previous_submission = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id, Submission.student_id == student.id)
        .first()
    )
    if previous_submission and not assignment.allow_multiple_submissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one submission is allowed for this assignment.",
        )

    file_path: str | None = None
    saved_upload_path: Path | None = None
    if file and file.filename:
        extension = Path(file.filename).suffix
        safe_name = f"{uuid4().hex}{extension}"
        output_path = UPLOAD_DIR / safe_name
        with output_path.open("wb") as output_file:
            output_file.write(file.file.read())
        saved_upload_path = output_path
        # Store a stable relative path so DB records remain valid across
        # different runtime locations (local shell, uvicorn cwd, docker, etc.).
        file_path = str(Path("uploads") / safe_name)

    if not text and not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide answer text or upload a file")

    submission = Submission(
        assignment_id=assignment_id,
        student_id=student.id,
        text=text,
        file_path=file_path,
    )
    db.add(submission)
    db.flush()
    submission_id = submission.id
    try:
        db.commit()
    except OperationalError:
        db.rollback()
        _unlink_stored_upload(file_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is busy or locked. Close other apps using app.db and try again.",
        ) from None

    # End transaction before OCR/ML so SQLite is not write-locked for minutes during grading.
    try:
        ml_result = evaluate_submission(
            student_id=student.id,
            assignment_id=assignment.id,
            submission_id=submission_id,
            title=assignment.title,
            description=assignment.description,
            reference_answer=assignment.reference_answer,
            reference_keywords=assignment.reference_keywords,
            reference_concepts=assignment.reference_concepts,
            text=text,
            file_path=file_path,
        )

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
            submission_id=submission_id,
            score=float(final_eval.get("marks_obtained", 0.0)),
            grade=str(final_eval.get("grade", "D")),
            feedback=bundle_evaluation(ml_result),
            created_by=assignment.created_by,
        )
        db.add(result)
        db.commit()
        saved = db.query(Submission).filter(Submission.id == submission_id).first()
        if not saved:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submission not found after grading.")
        return saved
    except HTTPException:
        db.rollback()
        _delete_submission_row(db, submission_id)
        _unlink_stored_upload(file_path)
        raise
    except Exception as exc:
        db.rollback()
        _delete_submission_row(db, submission_id)
        _unlink_stored_upload(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML evaluation failed during submission: {exc}",
        ) from exc


@router.get("/submissions/{assignment_id}", response_model=list[SubmissionOut])
def list_submissions(
    assignment_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment or assignment.created_by != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access submissions")

    return db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
