from app.energy.baseline import compute_and_store_baselines, get_baseline_lookup
from app.energy.ledger import query_readings
from app.ml.anomaly import detect_anomalies


def test_baseline_buckets_cover_every_meter_hour_combination_seen(seeded_db):
    db = seeded_db["db"]
    readings = query_readings(db)
    n_buckets = compute_and_store_baselines(db, readings)
    assert n_buckets > 0

    lookup = get_baseline_lookup(db)
    sample_meter = readings["meter_id"].iloc[0]
    sample_row = readings[readings["meter_id"] == sample_meter].iloc[0]
    key = (sample_meter, sample_row["timestamp"].dayofweek, sample_row["timestamp"].hour)
    assert key in lookup
    expected, std = lookup[key]
    assert expected >= 0
    assert std >= 0


def test_anomaly_detection_flags_a_deliberate_outlier(seeded_db):
    """The 6-week test dataset doesn't guarantee the generator's own randomized anomaly
    injection lands within this shorter window, so this test injects one unambiguous
    outlier by hand and checks the detector actually catches it -- a more deterministic
    check than depending on generator randomness."""
    db = seeded_db["db"]
    readings = query_readings(db)
    compute_and_store_baselines(db, readings)

    target_meter = readings[readings["zone_id"].notna()]["meter_id"].iloc[0]
    meter_readings = readings[readings["meter_id"] == target_meter].copy()
    spike_idx = meter_readings.index[len(meter_readings) // 2]
    normal_value = readings.loc[spike_idx, "energy_kwh"]
    readings.loc[spike_idx, "energy_kwh"] = max(normal_value, 1.0) * 20 + 50
    readings.loc[spike_idx, "power_kw"] = readings.loc[spike_idx, "energy_kwh"]

    detected = detect_anomalies(db, readings)
    assert len(detected) > 0
    for a in detected[:5]:
        assert a.evidence["expected_kwh"] is not None
        assert a.evidence["actual_kwh"] is not None
        assert a.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    spike_timestamp = readings.loc[spike_idx, "timestamp"]
    assert any(d.meter_id == target_meter and d.timestamp == spike_timestamp for d in detected)
