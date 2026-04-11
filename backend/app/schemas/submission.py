from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class SubmissionUploadMeta(BaseModel):
    assignment_id: int
    language_hint: str = Field(default="en", description="en or hi for OCR/normalization hint")


class OCRResult(BaseModel):
    text: str
    preprocessing_notes: list[str] = Field(default_factory=list)


class Explainability(BaseModel):
    semantic_component: float
    keyword_component: float
    plagiarism_penalty: float = 0.0
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    rationale: str


class FeedbackOut(BaseModel):
    summary: str
    missing_concepts: list[Any] = Field(default_factory=list)
    weak_areas: list[Any] = Field(default_factory=list)
    suggestions: list[Any] = Field(default_factory=list)
    attention_highlights: list[Any] = Field(default_factory=list)


class ScoreOut(BaseModel):
    id: int
    auto_score: Decimal
    final_score: Optional[Decimal]
    semantic_similarity: Decimal
    keyword_score: Decimal
    plagiarism_score: Optional[Decimal]
    explainability: Optional[dict[str, Any]] = None
    model_answer_id: int
    question_key: Optional[str] = None
    feedback: Optional[FeedbackOut] = None

    model_config = {"from_attributes": True}


class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    original_filename: Optional[str]
    status: str
    extracted_text: Optional[str]
    language_hint: str
    batch_id: Optional[str]
    created_at: datetime
    scores: list[ScoreOut] = []

    model_config = {"from_attributes": True}


class TeacherOverrideBody(BaseModel):
    final_score: Decimal
    note: Optional[str] = None


class EvaluateRequest(BaseModel):
    model_answer_id: int
    run_plagiarism: bool = True
