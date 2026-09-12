from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, get_current_user
from app.domain.structure import Asset, Meter, Zone

router = APIRouter(prefix="/api", tags=["structure"])


@router.get("/zones")
def list_zones(
    building_id: str | None = None,
    floor_id: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    query = db.query(Zone)
    if floor_id:
        query = query.filter(Zone.floor_id == floor_id)
    zones = query.all()
    if building_id:
        from app.domain.structure import Floor

        floor_ids = {f.id for f in db.query(Floor).filter(Floor.building_id == building_id).all()}
        zones = [z for z in zones if z.floor_id in floor_ids]
    return [
        {
            "id": z.id,
            "floor_id": z.floor_id,
            "name": z.name,
            "zone_type": z.zone_type,
            "area_sqm": z.area_sqm,
            "max_occupancy": z.max_occupancy,
        }
        for z in zones
    ]


@router.get("/zones/{zone_id}")
def get_zone(zone_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    z = db.query(Zone).filter(Zone.id == zone_id).first()
    if not z:
        raise GridMindError("NOT_FOUND", f"Zone '{zone_id}' not found", status_code=404)
    assets = db.query(Asset).filter(Asset.zone_id == zone_id).all()
    meters = db.query(Meter).filter(Meter.zone_id == zone_id).all()
    return {
        "id": z.id,
        "floor_id": z.floor_id,
        "name": z.name,
        "zone_type": z.zone_type,
        "area_sqm": z.area_sqm,
        "max_occupancy": z.max_occupancy,
        "assets": [
            {"id": a.id, "name": a.name, "asset_type": a.asset_type, "rated_power_kw": a.rated_power_kw}
            for a in assets
        ],
        "meters": [m.id for m in meters],
    }


@router.get("/assets")
def list_assets(
    zone_id: str | None = None,
    asset_type: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    query = db.query(Asset)
    if zone_id:
        query = query.filter(Asset.zone_id == zone_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    return [
        {
            "id": a.id,
            "zone_id": a.zone_id,
            "name": a.name,
            "asset_type": a.asset_type,
            "rated_power_kw": a.rated_power_kw,
            "install_year": a.install_year,
        }
        for a in query.all()
    ]


@router.get("/assets/{asset_id}")
def get_asset_health(asset_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    """Heuristic asset health indicator -- explicitly labeled as heuristic, not a trained
    predictive-maintenance model."""
    import pandas as pd

    from app.energy.ledger import query_readings

    a = db.query(Asset).filter(Asset.id == asset_id).first()
    if not a:
        raise GridMindError("NOT_FOUND", f"Asset '{asset_id}' not found", status_code=404)

    meter = db.query(Meter).filter(Meter.asset_id == asset_id).first()
    if not meter:
        return {"id": a.id, "name": a.name, "asset_type": a.asset_type, "health": "UNKNOWN", "note": "No meter attached"}

    readings = query_readings(db, meter_id=meter.id)
    if readings.empty:
        return {"id": a.id, "name": a.name, "asset_type": a.asset_type, "health": "UNKNOWN"}

    recent = readings.tail(24 * 7)
    avg_power = float(recent["power_kw"].mean())
    utilization = min(avg_power / a.rated_power_kw, 1.5) if a.rated_power_kw else 0
    efficiency_pct = round(max(0, 100 - abs(utilization - 0.6) * 80), 1)

    if efficiency_pct >= 75:
        health = "GOOD"
    elif efficiency_pct >= 50:
        health = "FAIR"
    else:
        health = "POOR"

    return {
        "id": a.id,
        "name": a.name,
        "asset_type": a.asset_type,
        "rated_power_kw": a.rated_power_kw,
        "install_year": a.install_year,
        "current_power_kw": round(float(readings["power_kw"].iloc[-1]), 2),
        "avg_power_kw_7d": round(avg_power, 2),
        "runtime_hours_7d": int((recent["power_kw"] > 0.05 * a.rated_power_kw).sum()),
        "heuristic_efficiency_pct": efficiency_pct,
        "health": health,
        "health_is_heuristic": True,
        "health_note": "Heuristic asset health indicator derived from recent utilization vs. rated capacity; not a trained predictive-maintenance model.",
    }


@router.get("/meters")
def list_meters(
    building_id: str | None = None,
    zone_id: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    query = db.query(Meter)
    if building_id:
        query = query.filter(Meter.building_id == building_id)
    if zone_id:
        query = query.filter(Meter.zone_id == zone_id)
    return [
        {
            "id": m.id,
            "building_id": m.building_id,
            "zone_id": m.zone_id,
            "asset_id": m.asset_id,
            "meter_type": m.meter_type,
            "unit": m.unit,
        }
        for m in query.all()
    ]
