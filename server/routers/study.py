import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from server.db.database import get_db
from server.db.models import StudyHistory
from server.db.schemas import GenerateRequest, GradeRequest, KindergartenRequest
from server.workflow.agents.kindergarten_agent import KindergartenExampleAgent
from server.workflow.graph import (
    create_analysis_graph,
    create_grading_graph,
    create_quiz_graph,
)


router = APIRouter(prefix="/api/v1/study", tags=["study"])


@router.post("/analyze")
async def analyze_material(
    learner_level: str = Form(...),
    file: UploadFile = File(...),
):
    raw = await file.read()

    if not raw:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="이미지는 12MB 이하로 업로드하세요.")

    mime = file.content_type or "image/jpeg"
    if not mime.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드할 수 있습니다.")

    graph = create_analysis_graph()
    result = graph.invoke(
        {
            "learner_level": learner_level,
            "image_bytes": raw,
            "mime_type": mime,
        }
    )
    return result["analysis"]


@router.post("/generate")
def generate_quiz(request: GenerateRequest):
    result = create_quiz_graph().invoke(
        {
            "learner_level": request.learner_level,
            "analysis": request.analysis,
            "problem_types": request.problem_types,
            "question_count": request.question_count,
        }
    )
    return result["quiz"]


@router.post("/grade")
def grade_quiz(
    request: GradeRequest,
    db: Session = Depends(get_db),
):
    result = create_grading_graph().invoke(
        {
            "learner_level": request.learner_level,
            "quiz": request.quiz,
            "answers": request.answers,
            "analysis": {},
        }
    )

    grading = result["grading"]

    history = StudyHistory(
        learner_level=request.learner_level,
        source_name=request.source_name,
        score=grading.get("score", 0),
        total=grading.get("total", 0),
        weak_words=json.dumps(grading.get("weak_words", []), ensure_ascii=False),
        related_words=json.dumps(grading.get("related_words", []), ensure_ascii=False),
        result_json=json.dumps(grading, ensure_ascii=False),
    )

    db.add(history)
    db.commit()
    return grading


@router.post("/kindergarten-examples")
def kindergarten_examples(request: KindergartenRequest):
    return KindergartenExampleAgent().run(request.analysis)
