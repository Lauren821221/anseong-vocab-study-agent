from fastapi import FastAPI
from server.db.database import Base, engine
from server.routers import study

Base.metadata.create_all(bind=engine)
app=FastAPI(title="안성맞춤 수준별 단어 스터디 에이전트 API", version="2.0.0")
app.include_router(study.router)

@app.get("/")
def root(): return {"message":"안성맞춤 수준별 단어 스터디 에이전트 API is running"}
@app.get("/health")
def health(): return {"status":"ok"}
