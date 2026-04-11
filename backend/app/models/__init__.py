"""SQLAlchemy ORM models."""

from app.models.orm import Assignment, Feedback, ModelAnswer, PlagiarismFlag, Score, Submission, User

__all__ = [
    "User",
    "Assignment",
    "ModelAnswer",
    "Submission",
    "Score",
    "Feedback",
    "PlagiarismFlag",
]
