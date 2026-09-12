from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, get_current_user
from app.domain.system import Notification
from app.energy.alerts import sync_notifications

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    building_id: str | None = None,
    unread_only: bool = False,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    query = db.query(Notification)
    if building_id:
        query = query.filter(Notification.building_id == building_id)
    if unread_only:
        query = query.filter(Notification.is_read == False)  # noqa: E712
    rows = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return [
        {
            "id": n.id,
            "building_id": n.building_id,
            "notification_type": n.notification_type,
            "severity": n.severity,
            "title": n.title,
            "message": n.message,
            "entity_type": n.entity_type,
            "entity_id": n.entity_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.post("/sync")
def sync(db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    created = sync_notifications(db)
    return {"created": created}


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise GridMindError("NOT_FOUND", f"Notification '{notification_id}' not found", status_code=404)
    n.is_read = True
    db.commit()
    return {"id": n.id, "is_read": True}
