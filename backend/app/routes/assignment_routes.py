"""Assignments and model answers."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers import assignment_controller
from app.database import get_db
from app.dependencies import get_current_teacher, get_current_user
from app.models.orm import User
from app.schemas.assignment import AssignmentCreate, AssignmentOut

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentOut])
def list_assignments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AssignmentOut]:
    return assignment_controller.list_assignments(db)


@router.post("", response_model=AssignmentOut)
def create_assignment(
    body: AssignmentCreate,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
) -> AssignmentOut:
    return assignment_controller.create_assignment(db, teacher, body)


@router.get("/{assignment_id}", response_model=AssignmentOut)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AssignmentOut:
    return assignment_controller.get_assignment(db, assignment_id)
