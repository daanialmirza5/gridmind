import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, Role, get_current_user, require_role
from app.domain.intelligence import Anomaly
from app.energy.ledger import query_readings
from app.ml.anomaly import detect_anomalies, persist_anomalies

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


def _serialize(a: Anomaly) -> dict:
    return {
        "id": a.id,
        "meter_id": a.meter_id,
        "building_id": a.building_id,
        "timestamp": a.timestamp.isoformat(),
        "expected_kwh": a.expected_kwh,
        "actual_kwh": a.actual_kwh,
        "deviation_pct": a.deviation_pct,
        "severity": a.severity,
        "detection_method": a.detection_method,
        "probable_cause": a.probable_cause,
        "evidence": json.loads(a.evidence_json) if a.evidence_json else {},
    }


@router.get("")
def list_anomalies(
    building_id: str | None = None,
    severity: str | None = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    query = db.query(Anomaly)
    if building_id:
        query = query.filter(Anomaly.building_id == building_id)
    if severity:
        query = query.filter(Anomaly.severity == severity.upper())
    rows = query.order_by(Anomaly.timestamp.desc()).limit(limit).all()
    return [_serialize(a) for a in rows]


@router.get("/{anomaly_id}")
def get_anomaly(anomaly_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    a = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not a:
        raise GridMindError("NOT_FOUND", f"Anomaly '{anomaly_id}' not found", status_code=404)
    return _serialize(a)


@router.post("/detect")
def run_anomaly_detection(
    building_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_role(Role.ENERGY_MANAGER, Role.ANALYST, Role.ADMIN)),
):
    readings = query_readings(db, building_id=building_id)
    if readings.empty:
        raise GridMindError("NO_DATA", "No readings available for this building", status_code=404)
    detected = detect_anomalies(db, readings)
    persist_anomalies(db, detected)
    return {"building_id": building_id, "anomalies_detected": len(detected)}
