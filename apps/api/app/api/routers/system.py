from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.domain.structure import Meter
from app.energy.ledger import dataset_bounds

router = APIRouter(prefix="/api/system-health", tags=["system"])
settings = get_settings()


@router.get("")
def system_health(db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "OK"
    except Exception:
        db_status = "ERROR"

    _, latest = dataset_bounds(db)
    meters_online = db.query(Meter).count()

    return {
        "database": db_status,
        "meters_registered": meters_online,
        "last_successful_ingestion": latest.isoformat() if latest else None,
        "ai_provider_configured": settings.ai_provider,
        "environment": settings.gridmind_env,
    }
