from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, Role, get_current_user, require_role
from app.domain.structure import Building
from app.domain.system import AuditEvent
from app.energy.eui import compute_eui
from app.energy.ingestion import ingest_dataframe, parse_payload
from app.energy.ledger import kpi_summary, query_readings
from app.energy.quality import compute_data_quality_report

router = APIRouter(prefix="/api/energy", tags=["energy"])


@router.get("")
def get_energy_readings(
    building_id: str | None = None,
    zone_id: str | None = None,
    meter_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    granularity: str = Query("hourly", pattern="^(hourly|daily|weekly|monthly)$"),
    limit: int = Query(2000, le=20000),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    df = query_readings(db, building_id=building_id, zone_id=zone_id, meter_id=meter_id, start=start, end=end)
    if df.empty:
        return {"granularity": granularity, "points": []}

    freq_map = {"hourly": "h", "daily": "D", "weekly": "W", "monthly": "MS"}
    resampled = (
        df.set_index("timestamp")
        .resample(freq_map[granularity])
        .agg({"energy_kwh": "sum", "power_kw": "max", "temperature_c": "mean", "occupancy": "mean"})
        .dropna(how="all")
        .tail(limit)
    )
    return {
        "granularity": granularity,
        "points": [
            {
                "timestamp": ts.isoformat(),
                "energy_kwh": round(float(row["energy_kwh"]), 2),
                "peak_power_kw": round(float(row["power_kw"]), 2),
                "avg_temperature_c": round(float(row["temperature_c"]), 1) if row["temperature_c"] == row["temperature_c"] else None,
                "avg_occupancy": round(float(row["occupancy"]), 1) if row["occupancy"] == row["occupancy"] else None,
            }
            for ts, row in resampled.iterrows()
        ],
    }


@router.get("/summary")
def get_energy_summary(
    building_id: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)
):
    return kpi_summary(db, building_id)


@router.get("/eui")
def get_eui(building_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise GridMindError("NOT_FOUND", f"Building '{building_id}' not found", status_code=404)

    df = query_readings(db, building_id=building_id)
    if df.empty:
        raise GridMindError("NO_DATA", "No readings available for this building", status_code=404)

    main = df[df["zone_id"].isna()]
    main = main.set_index("timestamp")
    latest = main.index.max()
    current_period = main[main.index >= latest - pd.Timedelta(days=30)]["energy_kwh"].sum()
    previous_period = main[
        (main.index < latest - pd.Timedelta(days=30)) & (main.index >= latest - pd.Timedelta(days=60))
    ]["energy_kwh"].sum()

    result = compute_eui(float(current_period), building.area_sqm, float(previous_period) if previous_period else None)
    return {"building_id": building_id, "area_sqm": building.area_sqm, **result.__dict__}


@router.get("/quality")
def get_data_quality(
    building_id: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)
):
    report = compute_data_quality_report(db, building_id)
    return report.__dict__


@router.post("/ingest")
def ingest_energy_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(Role.ENERGY_MANAGER, Role.FACILITY_MANAGER, Role.ADMIN)),
):
    raw = file.file.read()
    df = parse_payload(raw, file.content_type or "")
    report = ingest_dataframe(db, df, source_label=f"csv_import:{file.filename}")

    db.add(
        AuditEvent(
            actor=user.username,
            action="DATA_IMPORTED",
            entity_type="ingestion",
            entity_id=file.filename or "upload",
            new_state=str(report.__dict__),
            reason="Manual CSV/JSON energy data import",
        )
    )
    db.commit()
    return report.__dict__
