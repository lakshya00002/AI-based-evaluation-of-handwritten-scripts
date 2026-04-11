"""Registration and token issuance."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.orm import User, UserRole
from app.schemas.auth import UserCreate, UserOut
from app.security import hash_password


def register_user(db: Session, body: UserCreate) -> UserOut:
    if db.query(User).filter(User.email == str(body.email)).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        role = UserRole(body.role)
    except ValueError:
        role = UserRole.student
    user = User(
        email=str(body.email),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=role,
        preferred_language=body.preferred_language,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


