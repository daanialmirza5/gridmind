import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.service import answer_question
from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, get_current_user
from app.domain.intelligence import AIInsight

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AnalyzeRequest(BaseModel):
    question: str
    building_id: str


@router.post("/analyze")
def analyze(
    payload: AnalyzeRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)
):
    if not payload.question.strip():
        raise GridMindError("INVALID_QUESTION", "Question must not be empty")
    insight = answer_question(db, payload.question, payload.building_id, created_by=user.username)
    return {
        "id": insight.id,
        "agent": insight.agent,
        "question": insight.question,
        "answer": insight.answer,
        "confidence": insight.confidence,
        "limitations": insight.limitations,
        "evidence": json.loads(insight.evidence_json),
        "provider": insight.provider,
        "created_at": insight.created_at.isoformat(),
    }


@router.get("/history")
def history(
    building_id: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)
):
    query = db.query(AIInsight)
    rows = query.order_by(AIInsight.created_at.desc()).limit(50).all()
    if building_id:
        rows = [r for r in rows if json.loads(r.evidence_json).get("building_id") == building_id]
    return [
        {
            "id": r.id,
            "agent": r.agent,
            "question": r.question,
            "answer": r.answer,
            "confidence": r.confidence,
            "provider": r.provider,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
