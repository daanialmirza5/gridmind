"""Ties the lever functions, comfort model, and cost/carbon engines together into one
end-to-end scenario simulation: baseline vs scenario, for a given building and window."""

from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.domain.energy import EmissionFactor, Tariff
from app.domain.structure import Asset, Zone
from app.energy.carbon import compute_emissions
from app.energy.cost import compute_cost
from app.energy.ledger import query_readings
from app.energy.schedule import is_operating_hour, load_schedule
from app.optimization.comfort import (
    ComfortAssessment,
    assess_after_hours_cutback,
    assess_lighting_reduction,
    assess_peak_shift,
    assess_setpoint_change,
)
from app.optimization.simulator import (
    ScenarioLevers,
    ScenarioMetrics,
    apply_after_hours_cutback,
    apply_lighting_reduction,
    apply_peak_shift,
    apply_setpoint_lever,
    objective_score,
)


@dataclass
class ScenarioSimulationResult:
    metrics: ScenarioMetrics
    comfort_impact: str
    comfort_violations: int
    comfort_notes: list[str]
    objective_score: float


def simulate(db: Session, building_id: str, levers: ScenarioLevers, objective: str = "balanced") -> ScenarioSimulationResult:
    readings = query_readings(db, building_id=building_id)
    if readings.empty:
        raise ValueError("No readings available for this building")

    tariff = db.query(Tariff).filter(Tariff.building_id == building_id).first()
    factor = db.query(EmissionFactor).first()
    schedule = load_schedule(db)
    zone_types = {z.id: z.zone_type for z in db.query(Zone).all()}
    rated_kw_by_asset = {a.id: a.rated_power_kw for a in db.query(Asset).all()}

    operating_mask = readings["timestamp"].apply(lambda ts: is_operating_hour(schedule, building_id, ts))

    # Physical levers (setpoint, after-hours cutback, lighting) are only meaningful on a
    # single-asset submeter, so they're applied to zone submeters only; the building main
    # meter (a sum of zones + base load) then inherits the total zone-level delta rather
    # than having a formula re-applied to an aggregate it doesn't physically correspond to.
    zone_mask = readings["zone_id"].notna()
    zone_rows = readings[zone_mask]
    main_rows = readings[~zone_mask]

    zone_energy = zone_rows["energy_kwh"].copy()
    rated_kw = zone_rows["asset_id"].map(rated_kw_by_asset).fillna(zone_rows["energy_kwh"].quantile(0.9))

    zone_energy = apply_setpoint_lever(
        zone_rows.assign(energy_kwh=zone_energy), levers.hvac_setpoint_delta_c, operating_mask.loc[zone_rows.index], rated_kw
    )
    zone_energy = apply_after_hours_cutback(
        zone_rows.assign(energy_kwh=zone_energy), levers.after_hours_cutback_hours, schedule, building_id
    )

    if levers.lighting_reduction_pct > 0:
        adjusted = zone_energy.copy()
        for zone_id, group_idx in zone_rows.groupby("zone_id").groups.items():
            zone_type = zone_types.get(zone_id)
            sub_df = zone_rows.loc[group_idx].assign(energy_kwh=zone_energy.loc[group_idx])
            adjusted.loc[group_idx] = apply_lighting_reduction(
                sub_df, levers.lighting_reduction_pct, operating_mask.loc[group_idx], zone_type
            )
        zone_energy = adjusted

    # Propagate the total zone-level change per timestamp up to the building main meter.
    zone_delta = (zone_energy - zone_rows["energy_kwh"]).groupby(zone_rows["timestamp"]).sum()
    main_energy = main_rows["energy_kwh"] + main_rows["timestamp"].map(zone_delta).fillna(0.0)

    scenario_energy = pd.concat([zone_energy, main_energy]).reindex(readings.index)

    if levers.peak_shift_kw > 0 and tariff is not None:
        scenario_energy = apply_peak_shift(readings.assign(energy_kwh=scenario_energy), levers.peak_shift_kw, tariff)

    scenario_energy = scenario_energy.clip(lower=0)
    scenario_readings = readings.assign(energy_kwh=scenario_energy, power_kw=scenario_energy)

    baseline_main = readings[readings["zone_id"].isna()]
    scenario_main = scenario_readings[scenario_readings["zone_id"].isna()]

    baseline_cost = compute_cost(readings, tariff) if tariff else None
    scenario_cost = compute_cost(scenario_readings, tariff) if tariff else None
    baseline_emissions = compute_emissions(readings, factor) if factor else None
    scenario_emissions = compute_emissions(scenario_readings, factor) if factor else None

    baseline_energy_kwh = float(readings["energy_kwh"].sum())
    scenario_energy_kwh = float(scenario_readings["energy_kwh"].sum())
    baseline_peak_kw = float(baseline_main["power_kw"].max()) if not baseline_main.empty else float(readings["power_kw"].max())
    scenario_peak_kw = float(scenario_main["power_kw"].max()) if not scenario_main.empty else float(scenario_readings["power_kw"].max())

    def pct(base, scen):
        return round(((scen - base) / base) * 100, 2) if base else 0.0

    metrics = ScenarioMetrics(
        baseline_energy_kwh=round(baseline_energy_kwh, 1),
        scenario_energy_kwh=round(scenario_energy_kwh, 1),
        baseline_cost=baseline_cost.total_cost if baseline_cost else 0.0,
        scenario_cost=scenario_cost.total_cost if scenario_cost else 0.0,
        baseline_peak_kw=round(baseline_peak_kw, 1),
        scenario_peak_kw=round(scenario_peak_kw, 1),
        baseline_emissions_kg=baseline_emissions.total_kg_co2e if baseline_emissions else 0.0,
        scenario_emissions_kg=scenario_emissions.total_kg_co2e if scenario_emissions else 0.0,
        energy_change_pct=pct(baseline_energy_kwh, scenario_energy_kwh),
        cost_change_pct=pct(baseline_cost.total_cost, scenario_cost.total_cost) if tariff else 0.0,
        peak_change_pct=pct(baseline_peak_kw, scenario_peak_kw),
        emissions_change_pct=pct(baseline_emissions.total_kg_co2e, scenario_emissions.total_kg_co2e) if factor else 0.0,
    )

    comfort_assessments: list[ComfortAssessment] = []
    if levers.hvac_setpoint_delta_c != 0:
        comfort_assessments.append(assess_setpoint_change(22.0, levers.hvac_setpoint_delta_c))
    if levers.after_hours_cutback_hours > 0:
        spillover = bool((readings["occupancy"].fillna(0) > 0).any())
        comfort_assessments.append(assess_after_hours_cutback(spillover))
    if levers.lighting_reduction_pct > 0:
        comfort_assessments.append(assess_lighting_reduction(levers.lighting_reduction_pct))
    if levers.peak_shift_kw > 0:
        comfort_assessments.append(assess_peak_shift())

    if not comfort_assessments:
        overall_impact, violations, notes = "None", 0, ["No levers applied."]
    else:
        rank = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
        overall_impact = max(comfort_assessments, key=lambda c: rank[c.impact]).impact
        violations = sum(c.violations for c in comfort_assessments)
        notes = [c.notes for c in comfort_assessments]

    score = objective_score(metrics, objective)

    return ScenarioSimulationResult(
        metrics=metrics,
        comfort_impact=overall_impact,
        comfort_violations=violations,
        comfort_notes=notes,
        objective_score=score,
    )
