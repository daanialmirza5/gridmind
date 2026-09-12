from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.domain.system import AuditEvent

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_events(
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    query = db.query(AuditEvent)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if action:
        query = query.filter(AuditEvent.action == action)
    rows = query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "actor": e.actor,
            "action": e.action,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "previous_state": e.previous_state,
            "new_state": e.new_state,
            "reason": e.reason,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in rows
    ]
