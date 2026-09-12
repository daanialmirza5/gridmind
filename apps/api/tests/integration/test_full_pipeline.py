"""End-to-end pipeline integration test:
import -> normalize -> baseline -> anomaly detection -> waste detection ->
recommendation -> forecast -> optimization scenario.

This exercises the same call sequence apps/api/seed/run_seed.py uses in production,
against a small in-memory dataset, so a regression in how the stages wire together
(not just each stage in isolation) gets caught.
"""

import pandas as pd

from app.domain.intelligence import WasteEvent
from app.energy.baseline import compute_and_store_baselines
from app.energy.ingestion import ingest_dataframe
from app.energy.ledger import query_readings
from app.energy.waste import detect_waste_events, persist_waste_events
from app.ml.anomaly import detect_anomalies, persist_anomalies
from app.ml.forecast import generate_forecast
from app.optimization.engine import simulate
from app.optimization.recommendations import generate_recommendations, persist_recommendations, prioritize
from app.optimization.simulator import PRESETS


def test_full_pipeline_runs_start_to_finish(seeded_db):
    db = seeded_db["db"]
    building_id = seeded_db["buildings"][0].id

    # 1. Ingestion: a fresh CSV-style import lands cleanly in the ledger.
    before_count = len(query_readings(db, building_id=building_id))
    new_row = pd.DataFrame(
        {
            "meter_id": [next(m.id for b in seeded_db["buildings"] if b.id == building_id for m in b.meters)],
            "timestamp": ["2026-03-05T00:00:00"],  # deliberately after the seeded dataset's end date
            "energy_kwh": [12.3],
        }
    )
    report = ingest_dataframe(db, new_row)
    assert report.rows_valid == 1
    after_count = len(query_readings(db, building_id=building_id))
    assert after_count == before_count + 1

    # 2. Baseline model.
    all_readings = query_readings(db)
    n_buckets = compute_and_store_baselines(db, all_readings)
    assert n_buckets > 0

    # 3. Anomaly detection on this building's readings.
    building_readings = query_readings(db, building_id=building_id)
    anomalies = detect_anomalies(db, building_readings)
    persist_anomalies(db, anomalies)

    # 4. Waste detection.
    waste_events = detect_waste_events(db, building_readings)
    persist_waste_events(db, waste_events)
    assert db.query(WasteEvent).filter(WasteEvent.building_id == building_id).count() == len(waste_events)

    # 5. Recommendations, prioritized and persisted.
    all_waste = db.query(WasteEvent).filter(WasteEvent.building_id == building_id).all()
    if all_waste:
        drafts = generate_recommendations(all_waste)
        scored = prioritize(drafts)
        persist_recommendations(db, scored)
        assert len(scored) == len(drafts)

    # 6. Forecast: only meaningful once there's enough history; this dataset is 6 weeks.
    main_series = building_readings[building_readings["zone_id"].isna()].set_index("timestamp")["energy_kwh"]
    forecast = generate_forecast(main_series, horizon_hours=24, method="holt_winters")
    assert len(forecast.points) == 24
    assert all(p.lower_kwh <= p.expected_kwh <= p.upper_kwh for p in forecast.points)

    # 7. Optimization scenario vs. this same building's baseline.
    result = simulate(db, building_id, PRESETS["balanced"], objective="balanced")
    assert result.metrics.scenario_energy_kwh <= result.metrics.baseline_energy_kwh
    assert result.comfort_impact in ("None", "Low", "Medium", "High")
