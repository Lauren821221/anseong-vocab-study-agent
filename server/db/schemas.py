from typing import Any, Dict, List
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    learner_level: str
    analysis: Dict[str, Any]
    problem_types: List[str]
    question_count: int = Field(default=10, ge=5, le=25)


class GradeRequest(BaseModel):
    learner_level: str
    quiz: Dict[str, Any]
    answers: Dict[str, str]
    source_name: str = ""


class KindergartenRequest(BaseModel):
    learner_level: str = "유치원"
    analysis: Dict[str, Any]
