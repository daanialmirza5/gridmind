from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, get_current_user
from app.domain.structure import Asset, Building, Floor, Meter, Zone
from app.energy.eui import compute_eui
from app.energy.ledger import kpi_summary, query_readings

router = APIRouter(prefix="/api/buildings", tags=["buildings"])


def _building_dict(b: Building) -> dict:
    return {
        "id": b.id,
        "organization_id": b.organization_id,
        "name": b.name,
        "address": b.address,
        "area_sqm": b.area_sqm,
        "timezone": b.timezone,
    }


@router.get("")
def list_buildings(db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    return [_building_dict(b) for b in db.query(Building).all()]


@router.get("/{building_id}")
def get_building(building_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    b = db.query(Building).filter(Building.id == building_id).first()
    if not b:
        raise GridMindError("NOT_FOUND", f"Building '{building_id}' not found", status_code=404)

    kpi = kpi_summary(db, building_id)
    eui = None
    if kpi.get("month_energy_kwh") is not None and b.area_sqm > 0:
        eui = compute_eui(kpi["month_energy_kwh"], b.area_sqm).__dict__

    return {**_building_dict(b), "kpi": kpi, "eui": eui}


@router.get("/{building_id}/twin")
def get_digital_twin(building_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    """Building -> Floors -> Zones -> Assets -> Meters, for the React Flow digital-twin graph."""
    b = db.query(Building).filter(Building.id == building_id).first()
    if not b:
        raise GridMindError("NOT_FOUND", f"Building '{building_id}' not found", status_code=404)

    floors = db.query(Floor).filter(Floor.building_id == building_id).order_by(Floor.level).all()
    meters_by_zone: dict[str, list[Meter]] = {}
    meters_by_asset: dict[str, list[Meter]] = {}
    for m in db.query(Meter).filter(Meter.building_id == building_id).all():
        if m.zone_id:
            meters_by_zone.setdefault(m.zone_id, []).append(m)
        if m.asset_id:
            meters_by_asset.setdefault(m.asset_id, []).append(m)

    tree = []
    for f in floors:
        zones = db.query(Zone).filter(Zone.floor_id == f.id).all()
        zone_nodes = []
        for z in zones:
            assets = db.query(Asset).filter(Asset.zone_id == z.id).all()
            zone_nodes.append(
                {
                    "id": z.id,
                    "name": z.name,
                    "zone_type": z.zone_type,
                    "area_sqm": z.area_sqm,
                    "max_occupancy": z.max_occupancy,
                    "meters": [m.id for m in meters_by_zone.get(z.id, [])],
                    "assets": [
                        {
                            "id": a.id,
                            "name": a.name,
                            "asset_type": a.asset_type,
                            "rated_power_kw": a.rated_power_kw,
                            "install_year": a.install_year,
                            "meters": [m.id for m in meters_by_asset.get(a.id, [])],
                        }
                        for a in assets
                    ],
                }
            )
        tree.append({"id": f.id, "name": f.name, "level": f.level, "zones": zone_nodes})

    main_meter = db.query(Meter).filter(Meter.building_id == building_id, Meter.meter_type == "main").first()
    return {"building": _building_dict(b), "main_meter_id": main_meter.id if main_meter else None, "floors": tree}


@router.get("/{building_id}/replay")
def replay_building_state(
    building_id: str,
    at: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    """Time-travel snapshot: what was happening in this building at a given hour."""
    import pandas as pd

    try:
        ts = pd.Timestamp(at)
    except Exception as exc:
        raise GridMindError("INVALID_TIMESTAMP", f"Could not parse timestamp '{at}'") from exc

    readings = query_readings(db, building_id=building_id, start=ts, end=ts + pd.Timedelta(hours=1))
    if readings.empty:
        raise GridMindError("NOT_FOUND", "No data available for this timestamp", status_code=404)

    zones = []
    for _, row in readings[readings["zone_id"].notna()].iterrows():
        zones.append(
            {
                "zone_id": row["zone_id"],
                "meter_id": row["meter_id"],
                "power_kw": round(float(row["power_kw"]), 2),
                "occupancy": None if pd.isna(row["occupancy"]) else int(row["occupancy"]),
                "operating_state": row["operating_state"],
            }
        )
    main = readings[readings["zone_id"].isna()]
    return {
        "building_id": building_id,
        "timestamp": ts.isoformat(),
        "temperature_c": round(float(readings["temperature_c"].iloc[0]), 1) if not readings.empty else None,
        "main_power_kw": round(float(main["power_kw"].iloc[0]), 2) if not main.empty else None,
        "zones": zones,
    }
