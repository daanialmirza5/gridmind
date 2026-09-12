import pandas as pd

from app.domain.structure import Building, Meter, Organization
from app.energy.ledger import kpi_summary


def test_kpi_summary_current_demand_matches_the_exact_latest_reading(db_session):
    """Regression test: kpi_summary's `current_demand_kw` used to always come back as 0
    because a raw-SQL `timestamp = :latest` comparison silently matched zero rows --
    pandas' to_sql stores timestamps with a forced 6-digit microsecond suffix
    ('...23:00:00.000000'), while a plain Python datetime bound through sqlite3's default
    adapter serializes as '...23:00:00' (no suffix) whenever microsecond == 0. The two
    never compared equal. See app/energy/ledger.py::_sql_dt for the fix."""
    db_session.add(Organization(id="org1", name="Org"))
    db_session.add(Building(id="b1", organization_id="org1", name="B1", area_sqm=100))
    db_session.add(Meter(id="MTR-MAIN", building_id="b1", meter_type="main"))
    db_session.commit()

    # An on-the-hour timestamp (microsecond == 0) is exactly the case that triggered the bug.
    readings = pd.DataFrame(
        {
            "meter_id": ["MTR-MAIN", "MTR-MAIN"],
            "building_id": ["b1", "b1"],
            "zone_id": [None, None],
            "asset_id": [None, None],
            "timestamp": [pd.Timestamp("2026-01-01 22:00:00"), pd.Timestamp("2026-01-01 23:00:00")],
            "energy_kwh": [40.0, 55.0],
            "power_kw": [40.0, 55.0],
            "temperature_c": [10.0, 10.0],
            "occupancy": [0, 0],
            "operating_state": ["unoccupied", "unoccupied"],
            "data_quality": ["valid", "valid"],
            "source": ["synthetic", "synthetic"],
        }
    )
    readings.to_sql("meter_readings", con=db_session.bind, if_exists="append", index=False)

    summary = kpi_summary(db_session, "b1")
    assert summary["current_demand_kw"] == 55.0
