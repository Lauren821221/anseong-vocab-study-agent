from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from server.db.database import Base


class StudyHistory(Base):
    __tablename__ = "study_history"

    id = Column(Integer, primary_key=True, index=True)
    learner_level = Column(String(50), nullable=False)
    source_name = Column(String(255), nullable=True)
    score = Column(Integer, default=0)
    total = Column(Integer, default=0)
    weak_words = Column(Text, nullable=True)
    related_words = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
