import pandas as pd
import pytest

from app.core.errors import GridMindError
from app.domain.structure import Building, Meter, Organization
from app.energy.ingestion import ingest_dataframe


@pytest.fixture()
def db_with_one_meter(db_session):
    db_session.add(Organization(id="org1", name="Org"))
    db_session.add(Building(id="b1", organization_id="org1", name="B1", area_sqm=100))
    db_session.add(Meter(id="MTR-0001", building_id="b1", meter_type="main"))
    db_session.commit()
    return db_session


def test_ingest_normalizes_wh_to_kwh(db_with_one_meter):
    df = pd.DataFrame(
        {"meter_id": ["MTR-0001"], "timestamp": ["2026-01-01T00:00:00"], "energy_wh": [5000]}
    )
    report = ingest_dataframe(db_with_one_meter, df)
    assert report.rows_valid == 1
    assert report.unit_conversions_applied == 1


def test_ingest_rejects_negative_energy(db_with_one_meter):
    df = pd.DataFrame(
        {"meter_id": ["MTR-0001"], "timestamp": ["2026-01-01T00:00:00"], "energy_kwh": [-5]}
    )
    report = ingest_dataframe(db_with_one_meter, df)
    assert report.rows_valid == 0
    assert report.rows_negative_rejected == 1


def test_ingest_rejects_unknown_meter(db_with_one_meter):
    df = pd.DataFrame(
        {"meter_id": ["MTR-9999"], "timestamp": ["2026-01-01T00:00:00"], "energy_kwh": [5]}
    )
    report = ingest_dataframe(db_with_one_meter, df)
    assert report.rows_valid == 0
    assert report.rows_rejected_unknown_meter == 1


def test_ingest_deduplicates_repeated_rows(db_with_one_meter):
    df = pd.DataFrame(
        {
            "meter_id": ["MTR-0001", "MTR-0001"],
            "timestamp": ["2026-01-01T00:00:00", "2026-01-01T00:00:00"],
            "energy_kwh": [5, 5],
        }
    )
    report = ingest_dataframe(db_with_one_meter, df)
    assert report.rows_valid == 1
    assert report.rows_deduplicated == 1


def test_ingest_second_call_dedupes_against_existing_ledger_rows(db_with_one_meter):
    df = pd.DataFrame({"meter_id": ["MTR-0001"], "timestamp": ["2026-01-01T00:00:00"], "energy_kwh": [5]})
    ingest_dataframe(db_with_one_meter, df)
    report_second = ingest_dataframe(db_with_one_meter, df)
    assert report_second.rows_valid == 0
    assert report_second.rows_deduplicated == 1


def test_parse_payload_requires_energy_column(db_with_one_meter):
    from app.energy.ingestion import parse_payload

    csv_bytes = b"meter_id,timestamp\nMTR-0001,2026-01-01T00:00:00\n"
    with pytest.raises(GridMindError):
        ingest_dataframe(db_with_one_meter, parse_payload(csv_bytes, "text/csv"))
