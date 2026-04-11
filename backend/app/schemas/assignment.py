from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelAnswerIn(BaseModel):
    question_key: str
    reference_text: str
    keywords: Optional[list[str]] = None
    weight: Decimal = Field(default=Decimal("1"))


class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    course_code: Optional[str] = None
    max_score: Decimal = Field(default=Decimal("100"))
    model_answers: list[ModelAnswerIn] = Field(default_factory=list)


class ModelAnswerOut(BaseModel):
    id: int
    question_key: str
    reference_text: str
    keywords_json: Optional[dict[str, Any]] = None
    weight: Decimal

    model_config = {"from_attributes": True}


class AssignmentOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    course_code: Optional[str]
    max_score: Decimal
    created_by: int
    created_at: datetime
    model_answers: list[ModelAnswerOut] = []

    model_config = {"from_attributes": True}
