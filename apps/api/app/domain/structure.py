"""Structural digital-twin hierarchy: Organization -> Building -> Floor -> Zone -> Asset -> Meter."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    buildings: Mapped[list["Building"]] = relationship(back_populates="organization")


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, default="")
    area_sqm: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    latitude: Mapped[float] = mapped_column(Float, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="buildings")
    floors: Mapped[list["Floor"]] = relationship(back_populates="building", cascade="all, delete-orphan")
    meters: Mapped[list["Meter"]] = relationship(back_populates="building")


class Floor(Base):
    __tablename__ = "floors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    building: Mapped["Building"] = relationship(back_populates="floors")
    zones: Mapped[list["Zone"]] = relationship(back_populates="floor", cascade="all, delete-orphan")


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    floor_id: Mapped[str] = mapped_column(ForeignKey("floors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    zone_type: Mapped[str] = mapped_column(String, default="office")  # office, server_room, common_area...
    area_sqm: Mapped[float] = mapped_column(Float, nullable=False)
    max_occupancy: Mapped[int] = mapped_column(Integer, default=20)

    floor: Mapped["Floor"] = relationship(back_populates="zones")
    assets: Mapped[list["Asset"]] = relationship(back_populates="zone", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    asset_type: Mapped[str] = mapped_column(String, nullable=False)  # hvac, lighting, equipment
    rated_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    install_year: Mapped[int] = mapped_column(Integer, default=2018)

    zone: Mapped["Zone"] = relationship(back_populates="assets")
    meters: Mapped[list["Meter"]] = relationship(back_populates="asset")


class Meter(Base):
    __tablename__ = "meters"
    __table_args__ = (UniqueConstraint("id", name="uq_meter_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    meter_type: Mapped[str] = mapped_column(String, default="submeter")  # main, submeter
    unit: Mapped[str] = mapped_column(String, default="kWh")

    building: Mapped["Building"] = relationship(back_populates="meters")
    zone: Mapped["Zone"] = relationship()
    asset: Mapped["Asset"] = relationship(back_populates="meters")
