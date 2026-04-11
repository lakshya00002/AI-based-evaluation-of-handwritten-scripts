#!/usr/bin/env python3
"""
Create demo teacher, student, and one assignment with a model answer.

Usage (from repo root, with API env / DB reachable):

  cd backend && pip install -r requirements.txt
  export DATABASE_URL=mysql+pymysql://assess:pass@localhost:3306/handwritten_assessment
  python ../scripts/seed_demo.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models.orm import Assignment, ModelAnswer, User, UserRole
from app.security import hash_password


def main() -> None:
    from app.database import Base

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "teacher@demo.edu").first():
            db.add(
                User(
                    email="teacher@demo.edu",
                    hashed_password=hash_password("teacherdemo"),
                    full_name="Demo Teacher",
                    role=UserRole.teacher,
                )
            )
        if not db.query(User).filter(User.email == "student@demo.edu").first():
            db.add(
                User(
                    email="student@demo.edu",
                    hashed_password=hash_password("studentdemo"),
                    full_name="Demo Student",
                    role=UserRole.student,
                )
            )
        db.commit()

        teacher = db.query(User).filter(User.email == "teacher@demo.edu").first()
        assert teacher

        if db.query(Assignment).filter(Assignment.title == "Demo: Photosynthesis").first():
            print("Demo assignment already exists.")
            return

        a = Assignment(
            title="Demo: Photosynthesis",
            description="Short answer on photosynthesis and energy conversion.",
            course_code="BIO101",
            max_score=Decimal("10"),
            created_by=teacher.id,
        )
        db.add(a)
        db.flush()
        db.add(
            ModelAnswer(
                assignment_id=a.id,
                question_key="q1",
                reference_text=(
                    "Photosynthesis converts light energy into chemical energy stored in glucose. "
                    "It occurs in chloroplasts using chlorophyll, water, and carbon dioxide to produce "
                    "oxygen and glucose."
                ),
                keywords_json={
                    "keywords": [
                        "photosynthesis",
                        "chloroplast",
                        "glucose",
                        "chlorophyll",
                        "carbon dioxide",
                        "oxygen",
                        "light energy",
                    ]
                },
            )
        )
        db.commit()
        print("Seeded teacher@demo.edu / teacherdemo, student@demo.edu / studentdemo, assignment 'Demo: Photosynthesis'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
