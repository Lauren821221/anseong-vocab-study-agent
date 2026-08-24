from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from server.db.database import Base

class StudyHistory(Base):
    __tablename__="study_history"
    id=Column(Integer, primary_key=True, index=True)
    learner_level=Column(String(50), nullable=False)
    difficulty=Column(String(50), nullable=False)
    title=Column(String(255), nullable=False)
    words=Column(Text, nullable=False)
    quiz_types=Column(Text, nullable=True)
    question_count=Column(Integer, default=0)
    score=Column(Integer, nullable=True)
    result=Column(Text, nullable=True)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
