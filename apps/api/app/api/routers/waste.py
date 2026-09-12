import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, Role, get_current_user, require_role
from app.domain.intelligence import WasteEvent
from app.energy.ledger import query_readings
from app.energy.waste import detect_waste_events, persist_waste_events

router = APIRouter(prefix="/api/waste-events", tags=["waste"])


def _serialize(e: WasteEvent) -> dict:
    return {
        "id": e.id,
        "building_id": e.building_id,
        "zone_id": e.zone_id,
        "asset_id": e.asset_id,
        "meter_id": e.meter_id,
        "rule": e.rule,
        "severity": e.severity,
        "window_start": e.window_start.isoformat(),
        "window_end": e.window_end.isoformat(),
        "estimated_waste_kwh": e.estimated_waste_kwh,
        "estimated_cost": e.estimated_cost,
        "estimated_emissions_kg": e.estimated_emissions_kg,
        "evidence": json.loads(e.evidence_json) if e.evidence_json else {},
    }


@router.get("")
def list_waste_events(
    building_id: str | None = None,
    rule: str | None = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    query = db.query(WasteEvent)
    if building_id:
        query = query.filter(WasteEvent.building_id == building_id)
    if rule:
        query = query.filter(WasteEvent.rule == rule)
    rows = query.order_by(WasteEvent.estimated_cost.desc()).limit(limit).all()
    return [_serialize(e) for e in rows]


@router.get("/{event_id}")
def get_waste_event(event_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    e = db.query(WasteEvent).filter(WasteEvent.id == event_id).first()
    if not e:
        raise GridMindError("NOT_FOUND", f"Waste event '{event_id}' not found", status_code=404)
    return _serialize(e)


@router.post("/detect")
def run_waste_detection(
    building_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_role(Role.ENERGY_MANAGER, Role.ANALYST, Role.ADMIN)),
):
    readings = query_readings(db, building_id=building_id)
    if readings.empty:
        raise GridMindError("NO_DATA", "No readings available for this building", status_code=404)
    events = detect_waste_events(db, readings)
    persist_waste_events(db, events)
    return {"building_id": building_id, "waste_events_detected": len(events)}
