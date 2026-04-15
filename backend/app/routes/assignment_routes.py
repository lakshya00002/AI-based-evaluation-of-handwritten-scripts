from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_teacher
from app.models import Assignment, User
from app.schemas import AssignmentCreate, AssignmentOut

router = APIRouter(tags=["assignments"])


@router.get("/assignments", response_model=list[AssignmentOut])
def get_assignments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "teacher":
        return db.query(Assignment).filter(Assignment.created_by == current_user.id).all()
    return db.query(Assignment).all()


@router.post("/assignments", response_model=AssignmentOut)
def create_assignment(
    payload: AssignmentCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    assignment = Assignment(
        title=payload.title,
        description=payload.description,
        created_by=teacher.id,
        due_date=payload.due_date,
        allow_multiple_submissions=payload.allow_multiple_submissions,
        reference_answer=payload.reference_answer,
        reference_keywords=payload.reference_keywords,
        reference_concepts=payload.reference_concepts,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment
