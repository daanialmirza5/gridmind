import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.domain import structure as domain_structure  # noqa: E402
from app.domain import energy as domain_energy  # noqa: E402
from app.domain import system as domain_system  # noqa: E402
from seed.structure import build_structure  # noqa: E402
from seed.timeseries import SCHEDULES, SyntheticEnergyGenerator  # noqa: E402


@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite database per test -- fast and fully isolated."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded_db(db_session):
    """A small (6-week) synthetic dataset loaded into the in-memory DB, for tests that
    need real structure + a real energy ledger without paying the full 6-month cost."""
    buildings = build_structure("org-test")
    db_session.add(domain_structure.Organization(id="org-test", name="Test Org"))
    for b in buildings:
        db_session.add(
            domain_structure.Building(
                id=b.id, organization_id=b.organization_id, name=b.name, address=b.address, area_sqm=b.area_sqm
            )
        )
        for f in b.floors:
            db_session.add(domain_structure.Floor(id=f.id, building_id=f.building_id, name=f.name, level=f.level))
            for z in f.zones:
                db_session.add(
                    domain_structure.Zone(
                        id=z.id, floor_id=z.floor_id, name=z.name, zone_type=z.zone_type,
                        area_sqm=z.area_sqm, max_occupancy=z.max_occupancy,
                    )
                )
                for a in z.assets:
                    db_session.add(
                        domain_structure.Asset(
                            id=a.id, zone_id=a.zone_id, name=a.name, asset_type=a.asset_type,
                            rated_power_kw=a.rated_power_kw, install_year=a.install_year,
                        )
                    )
        for m in b.meters:
            db_session.add(
                domain_structure.Meter(
                    id=m.id, building_id=m.building_id, zone_id=m.zone_id, asset_id=m.asset_id, meter_type=m.meter_type
                )
            )
        db_session.add(
            domain_energy.Tariff(
                id=f"tariff-{b.id}", building_id=b.id, name="Test Tariff", tariff_type="time_of_use",
                flat_rate_per_kwh=0.15, peak_rate_per_kwh=0.28, off_peak_rate_per_kwh=0.09,
                peak_start_hour=14, peak_end_hour=19, demand_charge_per_kw=12.0,
            )
        )
        sched = SCHEDULES[b.kind]
        for dow, window in sched.items():
            if window is None:
                db_session.add(
                    domain_energy.OperatingSchedule(building_id=b.id, day_of_week=dow, start_hour=0, end_hour=0, is_operating_day=False)
                )
            else:
                db_session.add(
                    domain_energy.OperatingSchedule(
                        building_id=b.id, day_of_week=dow, start_hour=window[0], end_hour=window[1], is_operating_day=True
                    )
                )
    db_session.add(
        domain_energy.EmissionFactor(id="ef-test", source="grid_average", region="TEST", factor_kg_co2e_per_kwh=0.4)
    )
    db_session.add(
        domain_system.User(username="test.manager", full_name="Test Manager", password_hash=hash_password("test-pass"), role="ENERGY_MANAGER")
    )
    db_session.commit()

    end = pd.Timestamp("2026-03-01")
    start = end - pd.Timedelta(days=42)
    generator = SyntheticEnergyGenerator(buildings, start, end, seed=99)
    readings_df, weather_df, occupancy_df, ground_truth = generator.generate()

    readings_df.to_sql("meter_readings", con=db_session.bind, if_exists="append", index=False)
    weather_df.to_sql("weather_records", con=db_session.bind, if_exists="append", index=False)
    occupancy_df.to_sql("occupancy_records", con=db_session.bind, if_exists="append", index=False)

    return {"db": db_session, "buildings": buildings, "ground_truth": ground_truth}
