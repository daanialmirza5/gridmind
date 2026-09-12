"""Entry point: builds the digital twin, generates 6 months of synthetic energy data,
loads it into the configured database, and computes derived baselines.

Usage (from apps/api):
    python -m seed.run_seed
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.domain import structure as domain_structure  # noqa: E402
from app.domain import energy as domain_energy  # noqa: E402
from app.domain import system as domain_system  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.energy.ingestion import ingest_dataframe  # noqa: E402
from seed.structure import build_structure  # noqa: E402
from seed.timeseries import SCHEDULES, SyntheticEnergyGenerator  # noqa: E402

ORG_ID = "org-gridmind-demo"
SEED = 42
END = pd.Timestamp("2026-09-11 00:00:00")
START = END - pd.Timedelta(days=182)

DEMO_USERS = [
    ("energy.manager", "Erin Novak", "ENERGY_MANAGER"),
    ("facility.manager", "Marcus Reyes", "FACILITY_MANAGER"),
    ("analyst", "Priya Shah", "ANALYST"),
    ("executive", "Chen Wu", "EXECUTIVE"),
    ("admin", "Sam Okafor", "ADMIN"),
]
DEMO_PASSWORD = "gridmind-demo"


def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def load_structure(db, buildings):
    db.add(domain_structure.Organization(id=ORG_ID, name="GridMind Demo Organization"))
    for b in buildings:
        db.add(
            domain_structure.Building(
                id=b.id,
                organization_id=b.organization_id,
                name=b.name,
                address=b.address,
                area_sqm=b.area_sqm,
                timezone="UTC",
            )
        )
        for f in b.floors:
            db.add(domain_structure.Floor(id=f.id, building_id=f.building_id, name=f.name, level=f.level))
            for z in f.zones:
                db.add(
                    domain_structure.Zone(
                        id=z.id,
                        floor_id=z.floor_id,
                        name=z.name,
                        zone_type=z.zone_type,
                        area_sqm=z.area_sqm,
                        max_occupancy=z.max_occupancy,
                    )
                )
                for a in z.assets:
                    db.add(
                        domain_structure.Asset(
                            id=a.id,
                            zone_id=a.zone_id,
                            name=a.name,
                            asset_type=a.asset_type,
                            rated_power_kw=a.rated_power_kw,
                            install_year=a.install_year,
                        )
                    )
        for m in b.meters:
            db.add(
                domain_structure.Meter(
                    id=m.id,
                    building_id=m.building_id,
                    zone_id=m.zone_id,
                    asset_id=m.asset_id,
                    meter_type=m.meter_type,
                    unit=m.unit,
                )
            )
    db.commit()


def load_context(db, buildings):
    for b in buildings:
        db.add(
            domain_energy.Tariff(
                id=f"tariff-{b.id}",
                building_id=b.id,
                name="Demo Time-of-Use Tariff",
                tariff_type="time_of_use",
                currency="USD",
                flat_rate_per_kwh=0.15,
                peak_rate_per_kwh=0.28,
                off_peak_rate_per_kwh=0.09,
                peak_start_hour=14,
                peak_end_hour=19,
                demand_charge_per_kw=12.0,
                is_synthetic_assumption=True,
            )
        )
        sched = SCHEDULES[b.kind]
        for dow, window in sched.items():
            if window is None:
                db.add(
                    domain_energy.OperatingSchedule(
                        building_id=b.id, day_of_week=dow, start_hour=0, end_hour=0, is_operating_day=False
                    )
                )
            else:
                db.add(
                    domain_energy.OperatingSchedule(
                        building_id=b.id,
                        day_of_week=dow,
                        start_hour=window[0],
                        end_hour=window[1],
                        is_operating_day=True,
                    )
                )
    db.add(
        domain_energy.EmissionFactor(
            id="ef-grid-demo",
            source="grid_average",
            region="DEMO-REGION",
            factor_kg_co2e_per_kwh=0.417,
            unit="kgCO2e/kWh",
            is_synthetic_assumption=True,
        )
    )
    db.commit()


def load_users(db):
    for username, full_name, role in DEMO_USERS:
        db.add(
            domain_system.User(
                username=username,
                full_name=full_name,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
            )
        )
    db.commit()


def bulk_load_timeseries(readings_df: pd.DataFrame, weather_df: pd.DataFrame, occupancy_df: pd.DataFrame):
    readings_df.to_sql("meter_readings", con=engine, if_exists="append", index=False, chunksize=5000)
    weather_df.to_sql("weather_records", con=engine, if_exists="append", index=False, chunksize=5000)
    occupancy_df.to_sql("occupancy_records", con=engine, if_exists="append", index=False, chunksize=5000)


def run_intelligence_pipeline(db, buildings):
    from app.domain.intelligence import WasteEvent
    from app.energy.baseline import compute_and_store_baselines
    from app.energy.ledger import query_readings
    from app.energy.waste import detect_waste_events, persist_waste_events
    from app.ml.anomaly import detect_anomalies, persist_anomalies
    from app.optimization.recommendations import generate_recommendations, persist_recommendations, prioritize

    all_readings = query_readings(db)
    n_buckets = compute_and_store_baselines(db, all_readings)
    print(f"  baselines: {n_buckets} (meter, day-of-week, hour) buckets")

    total_anomalies = 0
    total_waste = 0
    for b in buildings:
        b_readings = query_readings(db, building_id=b.id)
        anomalies = detect_anomalies(db, b_readings)
        persist_anomalies(db, anomalies)
        total_anomalies += len(anomalies)

        waste = detect_waste_events(db, b_readings)
        persist_waste_events(db, waste)
        total_waste += len(waste)
    print(f"  anomalies detected: {total_anomalies}")
    print(f"  waste events detected: {total_waste}")

    all_waste = db.query(WasteEvent).all()
    drafts = generate_recommendations(all_waste)
    scored = prioritize(drafts)
    persist_recommendations(db, scored)
    print(f"  recommendations generated: {len(scored)}")

    from app.energy.alerts import sync_notifications

    n_notifications = sync_notifications(db)
    print(f"  notifications created: {n_notifications}")


def main():
    print("GridMind synthetic data generation")
    print(f"Window: {START} -> {END} (hourly)")

    buildings = build_structure(ORG_ID)

    print("Resetting database schema...")
    reset_database()

    db = SessionLocal()
    try:
        print("Loading building/floor/zone/asset/meter structure...")
        load_structure(db, buildings)
        print("Loading tariffs, emission factors, operating schedules...")
        load_context(db, buildings)
        print("Loading demo users...")
        load_users(db)
    finally:
        db.close()

    print("Generating synthetic hourly energy time-series (this can take a minute)...")
    generator = SyntheticEnergyGenerator(buildings, START, END, seed=SEED)
    readings_df, weather_df, occupancy_df, ground_truth = generator.generate()
    print(f"Generated {len(readings_df):,} meter readings across {readings_df['meter_id'].nunique()} meters")
    print(f"Injected {len(ground_truth)} ground-truth anomalies")

    # Hold back a small slice of rows to simulate real-world dropouts (never received),
    # producing genuine missing intervals rather than a hardcoded "data quality" number.
    quality_rng = np.random.default_rng(7)
    held_back_idx = quality_rng.choice(len(readings_df), size=int(len(readings_df) * 0.002), replace=False)
    held_back_df = readings_df.iloc[held_back_idx].copy()
    clean_df = readings_df.drop(index=held_back_idx).reset_index(drop=True)

    print("Bulk-loading time-series into database...")
    bulk_load_timeseries(clean_df, weather_df, occupancy_df)

    print("Simulating a follow-up CSV import (partial backfill + dirty rows)...")
    backfill_sample = held_back_df.sample(n=min(150, len(held_back_df)), random_state=7).copy()
    duplicate_sample = clean_df.sample(n=20, random_state=7).copy()  # already in the ledger -> should dedup
    negative_sample = clean_df.sample(n=15, random_state=8).copy()
    negative_sample["energy_kwh"] = -negative_sample["energy_kwh"].abs()
    unknown_meter_sample = clean_df.sample(n=10, random_state=9).copy()
    unknown_meter_sample["meter_id"] = "MTR-9999"

    dirty_import_df = pd.concat(
        [backfill_sample, duplicate_sample, negative_sample, unknown_meter_sample], ignore_index=True
    )[["meter_id", "timestamp", "energy_kwh", "power_kw", "temperature_c", "occupancy", "operating_state"]]

    db = SessionLocal()
    try:
        ingestion_report = ingest_dataframe(db, dirty_import_df, source_label="csv_import_demo")
    finally:
        db.close()
    print(
        f"Ingestion demo: received={ingestion_report.rows_received} valid={ingestion_report.rows_valid} "
        f"deduplicated={ingestion_report.rows_deduplicated} negative_rejected={ingestion_report.rows_negative_rejected} "
        f"unknown_meter_rejected={ingestion_report.rows_rejected_unknown_meter}"
    )

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(exist_ok=True)
    gt_path = out_dir / "ground_truth_anomalies.json"
    with open(gt_path, "w") as fh:
        json.dump(
            [
                {
                    "id": g.id,
                    "meter_id": g.meter_id,
                    "building_id": g.building_id,
                    "zone_id": g.zone_id,
                    "anomaly_type": g.anomaly_type,
                    "start": g.start.isoformat(),
                    "end": g.end.isoformat(),
                    "description": g.description,
                }
                for g in ground_truth
            ],
            fh,
            indent=2,
        )
    print(f"Ground-truth anomaly list written to {gt_path}")

    print("Running intelligence pipeline (baselines, anomalies, waste, recommendations)...")
    db = SessionLocal()
    try:
        run_intelligence_pipeline(db, buildings)
    finally:
        db.close()

    n_buildings = len(buildings)
    n_zones = sum(len(f.zones) for b in buildings for f in b.floors)
    n_assets = sum(len(z.assets) for b in buildings for f in b.floors for z in f.zones)
    n_meters = sum(len(b.meters) for b in buildings)
    print("")
    print("=== Seed summary ===")
    print(f"Buildings: {n_buildings}")
    print(f"Zones: {n_zones}")
    print(f"Assets: {n_assets}")
    print(f"Meters: {n_meters}")
    print(f"Readings: {len(readings_df):,}")
    print(f"Ground-truth anomalies: {len(ground_truth)}")
    print("Done.")


if __name__ == "__main__":
    main()
