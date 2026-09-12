import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, get_current_user
from app.domain.intelligence import Forecast
from app.energy.ledger import query_readings
from app.ml.forecast import evaluate_forecast, generate_forecast, predict_peak_demand

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])

HORIZON_HOURS = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30, "90d": 24 * 90}


def _main_series(db: Session, building_id: str):
    readings = query_readings(db, building_id=building_id)
    if readings.empty:
        return None
    main = readings[readings["zone_id"].isna()].set_index("timestamp")["energy_kwh"]
    return main


@router.post("")
def generate_and_store_forecast(
    building_id: str,
    horizon: str = Query("24h", pattern="^(24h|7d|30d|90d)$"),
    method: str = Query("holt_winters", pattern="^(holt_winters|seasonal_naive)$"),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    series = _main_series(db, building_id)
    if series is None:
        raise GridMindError("NO_DATA", "No readings available for this building", status_code=404)

    result = generate_forecast(series, HORIZON_HOURS[horizon], method=method)
    batch_id = f"FC-{uuid.uuid4().hex[:8]}"
    for p in result.points:
        db.add(
            Forecast(
                id=f"{batch_id}-{p.timestamp.isoformat()}",
                building_id=building_id,
                horizon=horizon,
                method=result.method,
                timestamp=p.timestamp,
                expected_kwh=p.expected_kwh,
                lower_kwh=p.lower_kwh,
                upper_kwh=p.upper_kwh,
            )
        )
    db.commit()
    return {
        "building_id": building_id,
        "horizon": horizon,
        "method": result.method,
        "residual_std": result.residual_std,
        "points": [p.__dict__ for p in result.points],
    }


@router.get("")
def get_latest_forecast(
    building_id: str,
    horizon: str = Query("24h", pattern="^(24h|7d|30d|90d)$"),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    series = _main_series(db, building_id)
    if series is None:
        raise GridMindError("NO_DATA", "No readings available for this building", status_code=404)
    result = generate_forecast(series, HORIZON_HOURS[horizon], method="holt_winters")
    return {
        "building_id": building_id,
        "horizon": horizon,
        "method": result.method,
        "points": [
            {
                "timestamp": p.timestamp.isoformat(),
                "expected_kwh": p.expected_kwh,
                "lower_kwh": p.lower_kwh,
                "upper_kwh": p.upper_kwh,
            }
            for p in result.points
        ],
    }


@router.get("/peak")
def get_peak_prediction(building_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    series = _main_series(db, building_id)
    if series is None:
        raise GridMindError("NO_DATA", "No readings available for this building", status_code=404)
    result = generate_forecast(series, 24, method="holt_winters")
    peak = predict_peak_demand(result, historical_peak_kw=float(series.max()))
    return {
        "building_id": building_id,
        "expected_peak_timestamp": peak.expected_peak_timestamp.isoformat(),
        "expected_peak_kw": peak.expected_peak_kw,
        "historical_peak_kw": peak.historical_peak_kw,
        "risk": peak.risk,
    }


@router.get("/evaluation")
def get_forecast_evaluation(building_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    series = _main_series(db, building_id)
    if series is None:
        raise GridMindError("NO_DATA", "No readings available for this building", status_code=404)

    results = []
    for label, hours in [("24h", 24), ("7d", 24 * 7), ("30d", 24 * 30)]:
        ev = evaluate_forecast(series, hours, method="holt_winters")
        if ev:
            results.append(ev.__dict__)
    return {"building_id": building_id, "evaluations": results}
