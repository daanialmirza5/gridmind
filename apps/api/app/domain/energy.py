"""Energy ledger and context records: readings, weather, occupancy, schedules, tariffs, emissions."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MeterReading(Base):
    """Normalized energy ledger record. One row per meter per hourly interval."""

    __tablename__ = "meter_readings"
    __table_args__ = (
        UniqueConstraint("meter_id", "timestamp", name="uq_meter_reading_interval"),
        Index("ix_meter_readings_meter_ts", "meter_id", "timestamp"),
        Index("ix_meter_readings_ts", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), nullable=False)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    zone_id: Mapped[str | None] = mapped_column(String, nullable=True)
    asset_id: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    energy_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=True)
    occupancy: Mapped[int] = mapped_column(Integer, nullable=True)
    operating_state: Mapped[str] = mapped_column(String, default="unknown")  # occupied, unoccupied
    data_quality: Mapped[str] = mapped_column(String, default="valid")  # valid, suspicious, duplicate, missing
    source: Mapped[str] = mapped_column(String, default="synthetic")  # synthetic, csv_import, json_import


class WeatherRecord(Base):
    __tablename__ = "weather_records"
    __table_args__ = (UniqueConstraint("building_id", "timestamp", name="uq_weather_interval"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_pct: Mapped[float] = mapped_column(Float, default=50.0)


class OccupancyRecord(Base):
    __tablename__ = "occupancy_records"
    __table_args__ = (UniqueConstraint("zone_id", "timestamp", name="uq_occupancy_interval"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    occupant_count: Mapped[int] = mapped_column(Integer, nullable=False)


class OperatingSchedule(Base):
    """Weekly operating hours per building (0=Monday ... 6=Sunday)."""

    __tablename__ = "operating_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    end_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    is_operating_day: Mapped[bool] = mapped_column(Boolean, default=True)


class Tariff(Base):
    """Configurable, clearly-synthetic tariff structure."""

    __tablename__ = "tariffs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    tariff_type: Mapped[str] = mapped_column(String, default="flat")  # flat, time_of_use
    currency: Mapped[str] = mapped_column(String, default="USD")
    flat_rate_per_kwh: Mapped[float] = mapped_column(Float, default=0.15)
    peak_rate_per_kwh: Mapped[float] = mapped_column(Float, default=0.28)
    off_peak_rate_per_kwh: Mapped[float] = mapped_column(Float, default=0.09)
    peak_start_hour: Mapped[int] = mapped_column(Integer, default=14)
    peak_end_hour: Mapped[int] = mapped_column(Integer, default=19)
    demand_charge_per_kw: Mapped[float] = mapped_column(Float, default=12.0)
    is_synthetic_assumption: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EmissionFactor(Base):
    """Configurable, clearly-synthetic emission factor (not an official government value)."""

    __tablename__ = "emission_factors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, default="grid_average")
    region: Mapped[str] = mapped_column(String, default="DEMO")
    factor_kg_co2e_per_kwh: Mapped[float] = mapped_column(Float, default=0.417)
    unit: Mapped[str] = mapped_column(String, default="kgCO2e/kWh")
    is_synthetic_assumption: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EnergyBaseline(Base):
    """Statistical baseline: expected consumption per meter/hour-of-week bucket."""

    __tablename__ = "energy_baselines"
    __table_args__ = (
        UniqueConstraint("meter_id", "day_of_week", "hour_of_day", name="uq_baseline_bucket"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    std_dev_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
