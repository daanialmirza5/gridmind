from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, get_current_user
from app.domain.energy import EmissionFactor
from app.energy.carbon import compute_emissions
from app.energy.ledger import query_readings

router = APIRouter(prefix="/api/carbon", tags=["carbon"])


@router.get("")
def get_carbon(
    building_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    readings = query_readings(db, building_id=building_id, start=start, end=end)
    main_only = readings[readings["zone_id"].isna()] if building_id is None else readings[readings["zone_id"].isna()]
    factor = db.query(EmissionFactor).first()
    if factor is None:
        raise GridMindError("NO_DATA", "No emission factor configured", status_code=404)

    result = compute_emissions(main_only if not main_only.empty else readings, factor)
    return {
        "building_id": building_id,
        "total_kg_co2e": result.total_kg_co2e,
        "factor_used": result.factor_used,
        "factor_source": result.factor_source,
        "factor_region": result.factor_region,
        "is_synthetic_assumption": result.is_synthetic_assumption,
    }
