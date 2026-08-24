from typing import Any, Dict, List, TypedDict


class StudyState(TypedDict, total=False):
    learner_level: str
    image_bytes: bytes
    mime_type: str
    analysis: Dict[str, Any]
    problem_types: List[str]
    question_count: int
    quiz: Dict[str, Any]
    answers: Dict[str, str]
    grading: Dict[str, Any]
    focus_words: List[str]
