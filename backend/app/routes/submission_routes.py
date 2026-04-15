from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_student, require_teacher
from app.ml_integration import evaluate_submission
from app.models import Assignment, Result, Submission, User
from app.schemas import SubmissionOut

router = APIRouter(tags=["submissions"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
            created_by=assignment.created_by,
        )
        db.add(result)
        db.commit()
        db.refresh(submission)
        return submission
    except HTTPException:
        db.rollback()
        if saved_upload_path and saved_upload_path.exists():
            saved_upload_path.unlink()
        raise
    except Exception as exc:
        db.rollback()
        if saved_upload_path and saved_upload_path.exists():
            saved_upload_path.unlink()
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
