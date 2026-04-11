"""Assignment CRUD for teachers."""

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.orm import Assignment, ModelAnswer, User, UserRole
from app.schemas.assignment import AssignmentCreate, AssignmentOut, ModelAnswerOut
from app.security import require_roles


def create_assignment(db: Session, teacher: User, body: AssignmentCreate) -> AssignmentOut:
    require_roles(teacher, UserRole.teacher)
    a = Assignment(
        title=body.title,
        description=body.description,
        course_code=body.course_code,
        max_score=body.max_score,
        created_by=teacher.id,
    )
    db.add(a)
    db.flush()
    for ma in body.model_answers:
        keywords_json = None
        if ma.keywords:
            keywords_json = {"keywords": ma.keywords}
        db.add(
            ModelAnswer(
                assignment_id=a.id,
                question_key=ma.question_key,
                reference_text=ma.reference_text,
                keywords_json=keywords_json,
                weight=ma.weight,
            )
        )
    db.commit()
    return get_assignment(db, a.id)


def get_assignment(db: Session, assignment_id: int) -> AssignmentOut:
    a = (
        db.query(Assignment)
        .options(joinedload(Assignment.model_answers))
        .filter(Assignment.id == assignment_id)
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    mas = [
        ModelAnswerOut(
            id=m.id,
            question_key=m.question_key,
            reference_text=m.reference_text,
            keywords_json=m.keywords_json,
            weight=m.weight,
        )
        for m in a.model_answers
    ]
    return AssignmentOut(
        id=a.id,
        title=a.title,
        description=a.description,
        course_code=a.course_code,
        max_score=a.max_score,
        created_by=a.created_by,
        created_at=a.created_at,
        model_answers=mas,
    )


def list_assignments(db: Session) -> list[AssignmentOut]:
    rows = db.query(Assignment).options(joinedload(Assignment.model_answers)).order_by(Assignment.id.desc()).all()
    out: list[AssignmentOut] = []
    for a in rows:
        mas = [
            ModelAnswerOut(
                id=m.id,
                question_key=m.question_key,
                reference_text=m.reference_text,
                keywords_json=m.keywords_json,
                weight=m.weight,
            )
            for m in a.model_answers
        ]
        out.append(
            AssignmentOut(
                id=a.id,
                title=a.title,
                description=a.description,
                course_code=a.course_code,
                max_score=a.max_score,
                created_by=a.created_by,
                created_at=a.created_at,
                model_answers=mas,
            )
        )
    return out
