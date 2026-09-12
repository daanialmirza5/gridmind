from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, get_current_user
from app.domain.energy import Tariff
from app.energy.cost import compute_cost
from app.energy.ledger import query_readings

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.get("")
def get_cost(
    building_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    tariff = db.query(Tariff).filter(Tariff.building_id == building_id).first()
    if not tariff:
        raise GridMindError("NOT_FOUND", f"No tariff configured for building '{building_id}'", status_code=404)

    readings = query_readings(db, building_id=building_id, start=start, end=end)
    main_only = readings[readings["zone_id"].isna()]
    result = compute_cost(main_only if not main_only.empty else readings, tariff)
    return {
        "building_id": building_id,
        "tariff_name": tariff.name,
        "tariff_type": tariff.tariff_type,
        "currency": result.currency,
        "consumption_cost": result.consumption_cost,
        "peak_cost": result.peak_cost,
        "off_peak_cost": result.off_peak_cost,
        "demand_cost": result.demand_cost,
        "total_cost": result.total_cost,
        "is_synthetic_assumption": result.is_synthetic_assumption,
    }
