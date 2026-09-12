"""Recommendation engine: turns detected waste events into prioritized, evidenced
recommendations. Every number shown is a rollup of actual WasteEvent rows -- nothing here
is invented independently of the detection engines.
"""

import json
import uuid
from collections import defaultdict
from dataclasses import dataclass

from app.domain.intelligence import Recommendation, WasteEvent

RULE_EFFORT = {
    "after_hours_hvac": "Low",
    "high_energy_low_occupancy": "Low",
    "excessive_standby_load": "Medium",
    "repeated_peak_demand_events": "Medium",
}

RULE_TITLES = {
    "after_hours_hvac": "Reduce after-hours HVAC runtime",
    "high_energy_low_occupancy": "Tighten HVAC/lighting response to low occupancy",
    "excessive_standby_load": "Investigate sustained elevated baseline load",
    "repeated_peak_demand_events": "Shift load to reduce repeated peak-demand events",
}

CONFIDENCE_SCORE = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 1.0}
EFFORT_SCORE = {"Low": 0.2, "Medium": 0.5, "High": 0.9}


def _confidence_for_count(n: int) -> str:
    if n >= 5:
        return "HIGH"
    if n >= 2:
        return "MEDIUM"
    return "LOW"


@dataclass
class RecommendationDraft:
    building_id: str
    zone_id: str | None
    rule: str
    title: str
    description: str
    estimated_energy_savings_kwh: float
    estimated_cost_savings: float
    estimated_emissions_reduction_kg: float
    estimated_peak_reduction_kw: float
    effort: str
    confidence: str
    occurrence_count: int
    evidence: dict


def generate_recommendations(waste_events: list[WasteEvent]) -> list[RecommendationDraft]:
    groups: dict[tuple, list[WasteEvent]] = defaultdict(list)
    for e in waste_events:
        groups[(e.building_id, e.zone_id, e.rule)].append(e)

    drafts = []
    for (building_id, zone_id, rule), events in groups.items():
        total_kwh = sum(e.estimated_waste_kwh for e in events)
        total_cost = sum(e.estimated_cost for e in events)
        total_emissions = sum(e.estimated_emissions_kg for e in events)
        confidence = _confidence_for_count(len(events))

        peak_reduction = 0.0
        if rule == "repeated_peak_demand_events":
            evidences = [json.loads(e.evidence_json) for e in events]
            max_powers = [ev.get("max_power_kw", 0) for ev in evidences]
            thresholds = [ev.get("peak_threshold_kw", 0) for ev in evidences]
            if max_powers and thresholds:
                peak_reduction = round(max(max_powers) - min(thresholds), 1)

        scope = f"zone {zone_id}" if zone_id else "the building main meter"
        description = (
            f"Over the analyzed period, {len(events)} '{rule}' event(s) were detected on {scope}, "
            f"totaling an estimated {total_kwh:.0f} kWh of avoidable consumption "
            f"(~{total_cost:.2f} in cost, ~{total_emissions:.0f} kg CO2e)."
        )

        drafts.append(
            RecommendationDraft(
                building_id=building_id,
                zone_id=zone_id,
                rule=rule,
                title=RULE_TITLES.get(rule, rule.replace("_", " ").title()),
                description=description,
                estimated_energy_savings_kwh=round(total_kwh, 1),
                estimated_cost_savings=round(total_cost, 2),
                estimated_emissions_reduction_kg=round(total_emissions, 1),
                estimated_peak_reduction_kw=peak_reduction,
                effort=RULE_EFFORT.get(rule, "Medium"),
                confidence=confidence,
                occurrence_count=len(events),
                evidence={
                    "rule": rule,
                    "occurrence_count": len(events),
                    "waste_event_ids": [e.id for e in events][:20],
                    "total_estimated_kwh": round(total_kwh, 1),
                    "total_estimated_cost": round(total_cost, 2),
                    "window_examples": [
                        {"start": e.window_start.isoformat(), "end": e.window_end.isoformat()} for e in events[:5]
                    ],
                },
            )
        )
    return drafts


def prioritize(drafts: list[RecommendationDraft]) -> list[tuple[RecommendationDraft, float]]:
    if not drafts:
        return []
    max_savings = max((d.estimated_cost_savings for d in drafts), default=1) or 1
    scored = []
    for d in drafts:
        savings_score = d.estimated_cost_savings / max_savings
        confidence_score = CONFIDENCE_SCORE[d.confidence]
        effort_score = EFFORT_SCORE[d.effort]
        priority = round(savings_score * 0.5 + confidence_score * 0.3 + (1 - effort_score) * 0.2, 4)
        scored.append((d, priority))
    return sorted(scored, key=lambda x: x[1], reverse=True)


def persist_recommendations(db, drafts_with_scores: list[tuple[RecommendationDraft, float]]) -> int:
    for draft, score in drafts_with_scores:
        db.add(
            Recommendation(
                id=f"REC-{uuid.uuid4().hex[:10]}",
                building_id=draft.building_id,
                title=draft.title,
                description=draft.description,
                source_type="waste_event",
                source_id=draft.rule,
                estimated_energy_savings_kwh=draft.estimated_energy_savings_kwh,
                estimated_cost_savings=draft.estimated_cost_savings,
                estimated_emissions_reduction_kg=draft.estimated_emissions_reduction_kg,
                estimated_peak_reduction_kw=draft.estimated_peak_reduction_kw,
                effort=draft.effort,
                confidence=draft.confidence,
                priority_score=score,
                status="SUGGESTED",
                evidence_json=json.dumps(draft.evidence, default=str),
            )
        )
    db.commit()
    return len(drafts_with_scores)
