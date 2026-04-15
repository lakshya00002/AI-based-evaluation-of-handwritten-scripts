from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Literal


RoleLiteral = Literal["student", "teacher"]


class SignupRequest(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    role: RoleLiteral


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: RoleLiteral

    class Config:
        from_attributes = True


class AssignmentCreate(BaseModel):
    title: str
    description: str
    due_date: datetime | None = None
    allow_multiple_submissions: bool = False
    reference_answer: str = ""
    reference_keywords: list[str] = Field(default_factory=list)
    reference_concepts: list[str] = Field(default_factory=list)


class AssignmentOut(BaseModel):
    id: int
    title: str
    description: str
    created_by: int
    due_date: datetime | None
    allow_multiple_submissions: bool

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    assignment_id: int
    text: str | None = None
    file_path: str | None = None


class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    file_path: str | None
    text: str | None
    submitted_at: datetime

    class Config:
        from_attributes = True


class ResultOut(BaseModel):
    id: int
    submission_id: int
    score: float
    grade: str
    feedback: dict
    created_by: int

    class Config:
        from_attributes = True


class ResultListOut(BaseModel):
    id: int
    submission_id: int
    assignment_id: int
    assignment_title: str
    student_id: int
    score: float
    grade: str
    feedback: dict
    ocr_extracted_text: str | None = None
    created_by: int
