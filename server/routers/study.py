import json
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from server.db.database import get_db
from server.db.models import StudyHistory, StudyMaterial
from server.workflow.agents.material_analyzer import MaterialAnalyzerAgent
from server.workflow.agents.recommender import RecommenderAgent
from server.workflow.agents.quiz_generator import QuizGeneratorAgent
from server.workflow.agents.grader import GraderAgent
from server.workflow.catalog import QUESTION_TYPES

router = APIRouter(prefix="/api/v1", tags=["study"])

class RecommendRequest(BaseModel):
    learner_level: str
    difficulty: str
    school_mode: str = "적용 안 함"
    words: list[dict]

class QuizRequest(BaseModel):
    learner_level: str
    difficulty: str
    school_mode: str = "적용 안 함"
    words: list[dict]
    type_ids: list[str]
    question_count: int

class GradeRequest(BaseModel):
    learner_level: str
    difficulty: str
    school_mode: str = "적용 안 함"
    title: str = "학습 자료"
    words: list[dict]
    type_ids: list[str]
    questions: list[dict]
    answers: dict

@router.get("/question-types")
def question_types():
    return [{"id": k, "name": v[0], "description": v[1]} for k, v in QUESTION_TYPES.items()]

@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    learner_level: str = Form(...),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "빈 파일입니다.")
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(413, "이미지는 15MB 이하로 올려주세요.")

    mime = file.content_type or "image/jpeg"
    allowed = ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif")
    if mime not in allowed:
        raise HTTPException(400, "JPG, PNG, WEBP, HEIC 계열 이미지를 사용해주세요.")

    result = MaterialAnalyzerAgent().run(raw, mime, learner_level)
    words = result.get("words", [])
    if not words:
        raise HTTPException(422, "사진에서 영어 학습 단어를 찾지 못했습니다.")

    material = StudyMaterial(
        title=result.get("title", "학습 자료"),
        learner_level=learner_level,
        summary=result.get("summary", ""),
        words=json.dumps(words, ensure_ascii=False),
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    result["material_id"] = material.id
    return result

@router.get("/materials")
def materials(db: Session = Depends(get_db)):
    rows = db.query(StudyMaterial).order_by(StudyMaterial.id.desc()).limit(100).all()
    return [{
        "id": r.id,
        "title": r.title,
        "learner_level": r.learner_level,
        "summary": r.summary or "",
        "words": json.loads(r.words or "[]"),
        "created_at": str(r.created_at),
    } for r in rows]

@router.get("/materials/{material_id}")
def material(material_id: int, db: Session = Depends(get_db)):
    r = db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
    if not r:
        raise HTTPException(404, "저장된 학습자료가 없습니다.")
    return {
        "id": r.id, "title": r.title, "learner_level": r.learner_level,
        "summary": r.summary or "", "words": json.loads(r.words or "[]"),
        "created_at": str(r.created_at),
    }

@router.post("/recommend")
def recommend(req: RecommendRequest):
    return RecommenderAgent().run(req.learner_level, req.difficulty, req.school_mode, req.words)

@router.post("/quiz")
def quiz(req: QuizRequest):
    if not req.type_ids:
        raise HTTPException(400, "문제 유형을 하나 이상 선택해주세요.")
    if req.question_count not in (5, 10, 15, 20, 25, 30):
        raise HTTPException(400, "지원하지 않는 문제 수입니다.")
    return QuizGeneratorAgent().run(
        req.learner_level, req.difficulty, req.school_mode,
        req.words, req.type_ids, req.question_count
    )

@router.post("/grade")
def grade(req: GradeRequest, db: Session = Depends(get_db)):
    result = GraderAgent().run(req.learner_level, req.questions, req.answers, req.words)
    result["school_mode"] = req.school_mode
    row = StudyHistory(
        learner_level=req.learner_level,
        difficulty=req.difficulty,
        title=req.title,
        words=json.dumps(req.words, ensure_ascii=False),
        quiz_types=json.dumps(req.type_ids, ensure_ascii=False),
        question_count=len(req.questions),
        score=result["score"],
        result=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    result["history_id"] = row.id
    return result

@router.get("/history")
def history(db: Session = Depends(get_db)):
    rows = db.query(StudyHistory).order_by(StudyHistory.id.desc()).limit(100).all()
    out = []
    for r in rows:
        result = json.loads(r.result or "{}")
        out.append({
            "id": r.id, "title": r.title, "learner_level": r.learner_level,
            "difficulty": r.difficulty, "school_mode": result.get("school_mode", "적용 안 함"),
            "quiz_types": json.loads(r.quiz_types or "[]"),
            "question_count": r.question_count, "score": r.score,
            "created_at": str(r.created_at), "words": json.loads(r.words or "[]"),
            "result": result,
        })
    return out

@router.delete("/history/{history_id}")
def delete_history(history_id: int, db: Session = Depends(get_db)):
    r = db.query(StudyHistory).filter(StudyHistory.id == history_id).first()
    if not r:
        raise HTTPException(404, "학습 이력이 없습니다.")
    db.delete(r)
    db.commit()
    return {"ok": True}
