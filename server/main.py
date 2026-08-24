import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.db.database import Base, engine
from server.db import models  # noqa: F401
from server.routers import history, study


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="안성맞춤 수준별 단어 스터디 에이전트 API",
    description=(
        "학습자료 이미지 분석, 수준별 문제 추천/생성, "
        "채점 및 단어 복습 코칭 API"
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(study.router)
app.include_router(history.router)


@app.get("/")
def root():
    return {
        "message": "안성맞춤 수준별 단어 스터디 에이전트 API is running"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
