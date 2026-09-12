"""Turns detected anomalies/waste events into Notification rows for the Alert Center.
Deliberately conservative thresholds (CRITICAL anomalies, HIGH+ waste) so the list stays
actionable rather than noisy."""

from sqlalchemy.orm import Session

from app.domain.intelligence import Anomaly, WasteEvent
from app.domain.system import Notification


def sync_notifications(db: Session) -> int:
    existing_keys = {(n.entity_type, n.entity_id) for n in db.query(Notification).all()}
    created = 0

    for a in db.query(Anomaly).filter(Anomaly.severity.in_(["HIGH", "CRITICAL"])).all():
        if ("anomaly", a.id) in existing_keys:
            continue
        db.add(
            Notification(
                building_id=a.building_id,
                notification_type="ANOMALY",
                severity=a.severity,
                title=f"{a.severity} anomaly on {a.meter_id}",
                message=f"{a.probable_cause}: {a.actual_kwh} kWh observed vs {a.expected_kwh} kWh expected ({a.deviation_pct}%).",
                entity_type="anomaly",
                entity_id=a.id,
            )
        )
        created += 1

    for w in db.query(WasteEvent).filter(WasteEvent.severity.in_(["HIGH", "CRITICAL"])).all():
        if ("waste_event", w.id) in existing_keys:
            continue
        db.add(
            Notification(
                building_id=w.building_id,
                notification_type="WASTE",
                severity=w.severity,
                title=f"{w.severity} waste pattern: {w.rule}",
                message=f"Estimated {w.estimated_waste_kwh} kWh (~{w.estimated_cost} cost) between {w.window_start} and {w.window_end}.",
                entity_type="waste_event",
                entity_id=w.id,
            )
        )
        created += 1

    db.commit()
    return created
