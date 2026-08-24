import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.db.database import get_db
from server.db.models import StudyHistory


router = APIRouter(
    prefix="/api/v1/history",
    tags=["history"],
)


@router.get("/")
def read_history(
    db: Session = Depends(get_db),
):
    rows = (
        db.query(StudyHistory)
        .order_by(StudyHistory.created_at.desc())
        .limit(50)
        .all()
    )

    result = []

    for row in rows:
        result.append(
            {
                "id": row.id,
                "learner_level": row.learner_level,
                "source_name": row.source_name,
                "score": row.score,
                "total": row.total,
                "weak_words": (
                    json.loads(row.weak_words)
                    if row.weak_words
                    else []
                ),
                "related_words": (
                    json.loads(row.related_words)
                    if row.related_words
                    else []
                ),
                "created_at": str(row.created_at),
            }
        )

    return result
