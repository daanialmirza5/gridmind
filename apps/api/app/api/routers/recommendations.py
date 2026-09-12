import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, Role, get_current_user, require_role
from app.domain.intelligence import Recommendation, WasteEvent
from app.domain.system import AuditEvent
from app.optimization.recommendations import generate_recommendations, persist_recommendations, prioritize

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _serialize(r: Recommendation) -> dict:
    return {
        "id": r.id,
        "building_id": r.building_id,
        "title": r.title,
        "description": r.description,
        "source_type": r.source_type,
        "source_id": r.source_id,
        "estimated_energy_savings_kwh": r.estimated_energy_savings_kwh,
        "estimated_cost_savings": r.estimated_cost_savings,
        "estimated_emissions_reduction_kg": r.estimated_emissions_reduction_kg,
        "estimated_peak_reduction_kw": r.estimated_peak_reduction_kw,
        "effort": r.effort,
        "confidence": r.confidence,
        "priority_score": r.priority_score,
        "status": r.status,
        "evidence": json.loads(r.evidence_json) if r.evidence_json else {},
        "created_at": r.created_at.isoformat(),
        "decided_by": r.decided_by,
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        "decision_reason": r.decision_reason,
        "disclaimer": "Estimated potential impact based on synthetic data and model assumptions -- not a guaranteed savings figure.",
    }


@router.get("")
def list_recommendations(
    building_id: str | None = None,
    status: str | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    query = db.query(Recommendation)
    if building_id:
        query = query.filter(Recommendation.building_id == building_id)
    if status:
        query = query.filter(Recommendation.status == status.upper())
    rows = query.order_by(Recommendation.priority_score.desc()).limit(limit).all()
    return [_serialize(r) for r in rows]


@router.post("/generate")
def generate_new_recommendations(
    building_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_role(Role.ENERGY_MANAGER, Role.ANALYST, Role.ADMIN)),
):
    events = db.query(WasteEvent).filter(WasteEvent.building_id == building_id).all()
    if not events:
        raise GridMindError("NO_DATA", "No waste events found -- run waste detection first", status_code=404)
    drafts = generate_recommendations(events)
    scored = prioritize(drafts)
    persist_recommendations(db, scored)
    return {"building_id": building_id, "recommendations_generated": len(scored)}


@router.get("/{recommendation_id}")
def get_recommendation(
    recommendation_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)
):
    r = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not r:
        raise GridMindError("NOT_FOUND", f"Recommendation '{recommendation_id}' not found", status_code=404)
    return _serialize(r)


class DecisionRequest(BaseModel):
    reason: str = ""


def _decide(
    db: Session, recommendation_id: str, new_status: str, user: CurrentUser, reason: str
) -> Recommendation:
    r = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not r:
        raise GridMindError("NOT_FOUND", f"Recommendation '{recommendation_id}' not found", status_code=404)

    previous_status = r.status
    r.status = new_status
    r.decided_by = user.username
    r.decided_at = datetime.now(timezone.utc)
    r.decision_reason = reason

    db.add(
        AuditEvent(
            actor=user.username,
            action=f"RECOMMENDATION_{new_status}",
            entity_type="recommendation",
            entity_id=r.id,
            previous_state=previous_status,
            new_state=new_status,
            reason=reason,
        )
    )
    db.commit()
    return r


@router.post("/{recommendation_id}/approve")
def approve_recommendation(
    recommendation_id: str,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(Role.ENERGY_MANAGER, Role.FACILITY_MANAGER, Role.ADMIN)),
):
    r = _decide(db, recommendation_id, "APPROVED", user, payload.reason)
    return _serialize(r)


@router.post("/{recommendation_id}/reject")
def reject_recommendation(
    recommendation_id: str,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(Role.ENERGY_MANAGER, Role.FACILITY_MANAGER, Role.ADMIN)),
):
    r = _decide(db, recommendation_id, "REJECTED", user, payload.reason)
    return _serialize(r)


@router.post("/{recommendation_id}/implement")
def implement_recommendation(
    recommendation_id: str,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(Role.ENERGY_MANAGER, Role.FACILITY_MANAGER, Role.ADMIN)),
):
    r = _decide(db, recommendation_id, "IMPLEMENTED", user, payload.reason)
    return _serialize(r)
