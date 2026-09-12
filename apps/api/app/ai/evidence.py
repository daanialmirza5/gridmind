"""Evidence retrieval: pulls structured facts from the deterministic engines for the AI
layer to explain. The AI never computes these numbers itself -- it only narrates them."""

import json

from sqlalchemy.orm import Session

from app.domain.energy import EmissionFactor
from app.domain.intelligence import Anomaly, Recommendation, WasteEvent
from app.energy.carbon import compute_emissions
from app.energy.ledger import kpi_summary, query_readings


def gather_anomaly_evidence(db: Session, building_id: str, limit: int = 5) -> dict:
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.building_id == building_id)
        .order_by(Anomaly.timestamp.desc())
        .limit(limit)
        .all()
    )
    return {
        "kind": "anomaly",
        "building_id": building_id,
        "anomalies": [
            {
                "meter_id": a.meter_id,
                "timestamp": a.timestamp.isoformat(),
                "expected_kwh": a.expected_kwh,
                "actual_kwh": a.actual_kwh,
                "deviation_pct": a.deviation_pct,
                "severity": a.severity,
                "probable_cause": a.probable_cause,
                "evidence": json.loads(a.evidence_json) if a.evidence_json else {},
            }
            for a in sorted(anomalies, key=lambda a: abs(a.deviation_pct), reverse=True)
        ],
    }


def gather_waste_evidence(db: Session, building_id: str, limit: int = 5) -> dict:
    events = (
        db.query(WasteEvent)
        .filter(WasteEvent.building_id == building_id)
        .order_by(WasteEvent.estimated_cost.desc())
        .limit(limit)
        .all()
    )
    return {
        "kind": "waste",
        "building_id": building_id,
        "waste_events": [
            {
                "meter_id": e.meter_id,
                "zone_id": e.zone_id,
                "rule": e.rule,
                "severity": e.severity,
                "window_start": e.window_start.isoformat(),
                "window_end": e.window_end.isoformat(),
                "estimated_waste_kwh": e.estimated_waste_kwh,
                "estimated_cost": e.estimated_cost,
                "estimated_emissions_kg": e.estimated_emissions_kg,
                "evidence": json.loads(e.evidence_json) if e.evidence_json else {},
            }
            for e in events
        ],
    }


def gather_forecast_evidence(db: Session, building_id: str) -> dict:
    from app.ml.forecast import generate_forecast

    readings = query_readings(db, building_id=building_id)
    main = readings[readings["zone_id"].isna()].set_index("timestamp")["energy_kwh"]
    try:
        result = generate_forecast(main, horizon_hours=24, method="holt_winters")
    except Exception:
        return {"kind": "forecast", "building_id": building_id, "forecast_points": []}

    return {
        "kind": "forecast",
        "building_id": building_id,
        "method": result.method,
        "forecast_points": [
            {
                "timestamp": p.timestamp.isoformat(),
                "expected_kwh": p.expected_kwh,
                "lower_kwh": p.lower_kwh,
                "upper_kwh": p.upper_kwh,
            }
            for p in result.points[:6]
        ],
    }


def gather_optimization_evidence(db: Session, building_id: str, objective: str = "balanced") -> dict:
    from app.optimization.engine import simulate
    from app.optimization.simulator import PRESETS

    try:
        result = simulate(db, building_id, PRESETS["balanced"], objective=objective)
    except ValueError:
        return {"kind": "optimization", "building_id": building_id, "scenario": None}

    return {
        "kind": "optimization",
        "building_id": building_id,
        "scenario": {
            "preset": "balanced",
            "energy_change_pct": result.metrics.energy_change_pct,
            "cost_change_pct": result.metrics.cost_change_pct,
            "peak_change_pct": result.metrics.peak_change_pct,
            "emissions_change_pct": result.metrics.emissions_change_pct,
            "comfort_impact": result.comfort_impact,
            "objective_score": result.objective_score,
        },
    }


def gather_carbon_evidence(db: Session, building_id: str) -> dict:
    readings = query_readings(db, building_id=building_id)
    factor = db.query(EmissionFactor).first()
    if readings.empty or factor is None:
        return {"kind": "carbon", "building_id": building_id, "emissions": None}
    result = compute_emissions(readings, factor)
    return {
        "kind": "carbon",
        "building_id": building_id,
        "emissions": {
            "total_kg_co2e": result.total_kg_co2e,
            "factor_used": result.factor_used,
            "factor_source": result.factor_source,
            "factor_region": result.factor_region,
            "is_synthetic_assumption": result.is_synthetic_assumption,
        },
    }


def gather_energy_evidence(db: Session, building_id: str) -> dict:
    return {"kind": "energy", "building_id": building_id, "kpi": kpi_summary(db, building_id)}


def gather_executive_evidence(db: Session, building_id: str) -> dict:
    kpi = kpi_summary(db, building_id)
    open_anomalies = db.query(Anomaly).filter(Anomaly.building_id == building_id).count()
    open_recs = (
        db.query(Recommendation)
        .filter(Recommendation.building_id == building_id, Recommendation.status == "SUGGESTED")
        .all()
    )
    return {
        "kind": "executive_summary",
        "building_id": building_id,
        "kpi": kpi,
        "open_anomalies": open_anomalies,
        "open_recommendations": len(open_recs),
        "total_potential_savings_cost": round(sum(r.estimated_cost_savings for r in open_recs), 2),
    }


EVIDENCE_GATHERERS = {
    "energy_analyst": gather_energy_evidence,
    "anomaly_analyst": gather_anomaly_evidence,
    "forecast_analyst": gather_forecast_evidence,
    "waste_analyst": gather_waste_evidence,
    "optimization_analyst": gather_optimization_evidence,
    "carbon_analyst": gather_carbon_evidence,
    "executive_narrator": gather_executive_evidence,
}
