from app.energy.baseline import compute_and_store_baselines
from app.energy.ledger import query_readings
from app.energy.waste import detect_waste_events


def test_waste_events_carry_evidence_and_nonnegative_estimates(seeded_db):
    db = seeded_db["db"]
    readings = query_readings(db)
    compute_and_store_baselines(db, readings)

    events = detect_waste_events(db, readings)
    assert isinstance(events, list)
    for e in events[:10]:
        assert e.estimated_waste_kwh >= 0
        assert e.rule in (
            "after_hours_hvac",
            "high_energy_low_occupancy",
            "excessive_standby_load",
            "repeated_peak_demand_events",
        )
        assert "rule" in e.evidence  # human-readable rule description for the "why" panel


def test_waste_detection_excludes_server_rooms_from_low_occupancy_rule(seeded_db):
    """Server rooms are legitimately always-on with low occupancy; this must not be
    treated as waste."""
    db = seeded_db["db"]
    readings = query_readings(db)
    compute_and_store_baselines(db, readings)
    events = detect_waste_events(db, readings)

    from app.domain.structure import Zone

    server_room_zone_ids = {z.id for z in db.query(Zone).filter(Zone.zone_type == "server_room").all()}
    low_occ_events = [e for e in events if e.rule == "high_energy_low_occupancy"]
    assert not any(e.zone_id in server_room_zone_ids for e in low_occ_events)
