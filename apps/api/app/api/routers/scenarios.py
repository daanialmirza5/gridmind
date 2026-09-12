import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import GridMindError
from app.core.security import CurrentUser, get_current_user
from app.domain.intelligence import OptimizationScenario, ScenarioResult
from app.optimization.engine import simulate
from app.optimization.simulator import PRESETS, ScenarioLevers

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


class LeversPayload(BaseModel):
    hvac_setpoint_delta_c: float = 0.0
    after_hours_cutback_hours: int = 0
    lighting_reduction_pct: float = 0.0
    peak_shift_kw: float = 0.0


class SimulateRequest(BaseModel):
    building_id: str
    levers: LeversPayload | None = None
    preset: str | None = None  # conservative | balanced | aggressive
    objective: str = "balanced"


def _resolve_levers(payload: SimulateRequest) -> ScenarioLevers:
    if payload.preset:
        if payload.preset not in PRESETS:
            raise GridMindError("INVALID_SCENARIO", f"Unknown preset '{payload.preset}'")
        return PRESETS[payload.preset]
    if payload.levers:
        return ScenarioLevers(**payload.levers.model_dump())
    return ScenarioLevers()


def _run(db: Session, payload: SimulateRequest):
    levers = _resolve_levers(payload)
    try:
        result = simulate(db, payload.building_id, levers, objective=payload.objective)
    except ValueError as exc:
        raise GridMindError("NO_DATA", str(exc), status_code=404) from exc
    return levers, result


@router.post("/simulate")
def simulate_scenario(
    payload: SimulateRequest, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)
):
    """Dry-run: computes the scenario but does not persist it."""
    levers, result = _run(db, payload)
    return {
        "building_id": payload.building_id,
        "levers": levers.as_dict(),
        "objective": payload.objective,
        "metrics": result.metrics.__dict__,
        "comfort_impact": result.comfort_impact,
        "comfort_violations": result.comfort_violations,
        "comfort_notes": result.comfort_notes,
        "objective_score": result.objective_score,
    }


class CreateScenarioRequest(SimulateRequest):
    name: str


@router.post("")
def create_scenario(
    payload: CreateScenarioRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)
):
    levers, result = _run(db, payload)

    scenario_id = f"SCN-{uuid.uuid4().hex[:10]}"
    db.add(
        OptimizationScenario(
            id=scenario_id,
            building_id=payload.building_id,
            name=payload.name,
            objective=payload.objective,
            parameters_json=json.dumps(levers.as_dict()),
            created_by=user.username,
        )
    )
    db.add(
        ScenarioResult(
            id=f"SR-{uuid.uuid4().hex[:10]}",
            scenario_id=scenario_id,
            baseline_energy_kwh=result.metrics.baseline_energy_kwh,
            scenario_energy_kwh=result.metrics.scenario_energy_kwh,
            baseline_cost=result.metrics.baseline_cost,
            scenario_cost=result.metrics.scenario_cost,
            baseline_peak_kw=result.metrics.baseline_peak_kw,
            scenario_peak_kw=result.metrics.scenario_peak_kw,
            baseline_emissions_kg=result.metrics.baseline_emissions_kg,
            scenario_emissions_kg=result.metrics.scenario_emissions_kg,
            comfort_impact=result.comfort_impact,
            comfort_violations=result.comfort_violations,
            objective_score=result.objective_score,
        )
    )
    db.commit()
    return {"id": scenario_id, "metrics": result.metrics.__dict__, "comfort_impact": result.comfort_impact}


@router.get("")
def list_scenarios(
    building_id: str | None = None, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)
):
    query = db.query(OptimizationScenario)
    if building_id:
        query = query.filter(OptimizationScenario.building_id == building_id)
    scenarios = query.order_by(OptimizationScenario.created_at.desc()).all()

    results_by_scenario = {r.scenario_id: r for r in db.query(ScenarioResult).all()}
    out = []
    for s in scenarios:
        r = results_by_scenario.get(s.id)
        out.append(
            {
                "id": s.id,
                "building_id": s.building_id,
                "name": s.name,
                "objective": s.objective,
                "parameters": json.loads(s.parameters_json),
                "created_by": s.created_by,
                "created_at": s.created_at.isoformat(),
                "result": {
                    "energy_change_pct": round(
                        (r.scenario_energy_kwh - r.baseline_energy_kwh) / r.baseline_energy_kwh * 100, 2
                    )
                    if r and r.baseline_energy_kwh
                    else None,
                    "cost_change_pct": round((r.scenario_cost - r.baseline_cost) / r.baseline_cost * 100, 2)
                    if r and r.baseline_cost
                    else None,
                    "comfort_impact": r.comfort_impact if r else None,
                    "objective_score": r.objective_score if r else None,
                }
                if r
                else None,
            }
        )
    return out


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str, db: Session = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    s = db.query(OptimizationScenario).filter(OptimizationScenario.id == scenario_id).first()
    if not s:
        raise GridMindError("NOT_FOUND", f"Scenario '{scenario_id}' not found", status_code=404)
    r = db.query(ScenarioResult).filter(ScenarioResult.scenario_id == scenario_id).first()
    result = None
    if r:
        result = {
            "baseline_energy_kwh": r.baseline_energy_kwh,
            "scenario_energy_kwh": r.scenario_energy_kwh,
            "baseline_cost": r.baseline_cost,
            "scenario_cost": r.scenario_cost,
            "baseline_peak_kw": r.baseline_peak_kw,
            "scenario_peak_kw": r.scenario_peak_kw,
            "baseline_emissions_kg": r.baseline_emissions_kg,
            "scenario_emissions_kg": r.scenario_emissions_kg,
            "comfort_impact": r.comfort_impact,
            "comfort_violations": r.comfort_violations,
            "objective_score": r.objective_score,
        }
    return {
        "id": s.id,
        "building_id": s.building_id,
        "name": s.name,
        "objective": s.objective,
        "parameters": json.loads(s.parameters_json),
        "created_by": s.created_by,
        "created_at": s.created_at.isoformat(),
        "result": result,
    }
