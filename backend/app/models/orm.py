"""ORM entities mirroring `sql/schema.sql`."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class SubmissionStatus(str, enum.Enum):
    uploaded = "uploaded"
    ocr_done = "ocr_done"
    evaluated = "evaluated"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student)
    preferred_language: Mapped[str] = mapped_column(String(16), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    assignments_created: Mapped[list["Assignment"]] = relationship(
        back_populates="creator", foreign_keys="Assignment.created_by"
    )
    submissions: Mapped[list["Submission"]] = relationship(back_populates="student")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    course_code: Mapped[Optional[str]] = mapped_column(String(64))
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    max_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("100"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    creator: Mapped["User"] = relationship(
        back_populates="assignments_created", foreign_keys=[created_by]
    )
    model_answers: Mapped[list["ModelAnswer"]] = relationship(back_populates="assignment")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="assignment")


class ModelAnswer(Base):
    __tablename__ = "model_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    question_key: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_text: Mapped[str] = mapped_column(Text, nullable=False)
    keywords_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    assignment: Mapped["Assignment"] = relationship(back_populates="model_answers")
    scores: Mapped[list["Score"]] = relationship(back_populates="model_answer")

    __table_args__ = (UniqueConstraint("assignment_id", "question_key", name="uq_assignment_question"),)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    original_filename: Mapped[Optional[str]] = mapped_column(String(512))
    stored_path: Mapped[Optional[str]] = mapped_column(String(1024))
    mime_type: Mapped[Optional[str]] = mapped_column(String(128))
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    language_hint: Mapped[str] = mapped_column(String(16), default="en")
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus), default=SubmissionStatus.uploaded)
    batch_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
    student: Mapped["User"] = relationship(back_populates="submissions")
    scores: Mapped[list["Score"]] = relationship(back_populates="submission")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    model_answer_id: Mapped[int] = mapped_column(ForeignKey("model_answers.id", ondelete="CASCADE"))
    auto_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    final_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    semantic_similarity: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    keyword_score: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    plagiarism_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 6))
    explainability_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    graded_by_teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    submission: Mapped["Submission"] = relationship(back_populates="scores")
    model_answer: Mapped["ModelAnswer"] = relationship(back_populates="scores")
    feedback: Mapped[Optional["Feedback"]] = relationship(back_populates="score", uselist=False)

    __table_args__ = (UniqueConstraint("submission_id", "model_answer_id", name="uq_score_submission_model"),)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    score_id: Mapped[int] = mapped_column(ForeignKey("scores.id", ondelete="CASCADE"), unique=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    missing_concepts_json: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    weak_areas_json: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    suggestions_json: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    attention_highlights_json: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    score: Mapped["Score"] = relationship(back_populates="feedback")


class PlagiarismFlag(Base):
    __tablename__ = "plagiarism_flags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    compared_submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    similarity: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
