import pandas as pd

from app.domain.intelligence import WasteEvent
from app.optimization.recommendations import generate_recommendations, prioritize


def _waste_event(**overrides) -> WasteEvent:
    defaults = dict(
        id="W1", building_id="b1", zone_id="z1", asset_id="a1", meter_id="m1",
        rule="after_hours_hvac", severity="HIGH",
        window_start=pd.Timestamp("2026-01-01T18:00:00"), window_end=pd.Timestamp("2026-01-01T20:00:00"),
        estimated_waste_kwh=50.0, estimated_cost=10.0, estimated_emissions_kg=20.0,
        evidence_json="{}",
    )
    defaults.update(overrides)
    return WasteEvent(**defaults)


def test_recommendations_group_by_building_zone_and_rule():
    events = [
        _waste_event(id="W1"),
        _waste_event(id="W2"),  # same group -> should merge
        _waste_event(id="W3", zone_id="z2", rule="excessive_standby_load", estimated_cost=100.0),
    ]
    drafts = generate_recommendations(events)
    assert len(drafts) == 2
    merged = next(d for d in drafts if d.zone_id == "z1")
    assert merged.occurrence_count == 2
    assert merged.estimated_energy_savings_kwh == 100.0  # 2 x 50 kWh


def test_higher_savings_and_confidence_rank_first():
    events = [
        _waste_event(id="W1", zone_id="z1", estimated_cost=5.0),  # low savings, 1 occurrence -> LOW confidence
    ] + [
        _waste_event(id=f"W{i}", zone_id="z2", rule="excessive_standby_load", estimated_cost=50.0) for i in range(6)
    ]  # high savings, 6 occurrences -> HIGH confidence
    drafts = generate_recommendations(events)
    scored = prioritize(drafts)
    top_draft, top_score = scored[0]
    assert top_draft.zone_id == "z2"
    assert top_score == max(s for _, s in scored)


def test_low_effort_rule_beats_medium_effort_rule_at_equal_savings():
    events = [
        _waste_event(id="W1", zone_id="z1", rule="after_hours_hvac", estimated_cost=50.0),  # Low effort
        _waste_event(id="W2", zone_id="z2", rule="excessive_standby_load", estimated_cost=50.0),  # Medium effort
    ]
    drafts = generate_recommendations(events)
    scored = prioritize(drafts)
    scores_by_zone = {d.zone_id: s for d, s in scored}
    assert scores_by_zone["z1"] > scores_by_zone["z2"]


def test_prioritize_handles_empty_input():
    assert prioritize([]) == []
