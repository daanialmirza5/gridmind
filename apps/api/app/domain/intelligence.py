"""Intelligence-layer records: anomalies, waste events, forecasts, scenarios, recommendations, AI insights."""

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JSONText:
    """Helper mixin methods for storing JSON blobs in a Text column (SQLite/Postgres portable)."""

    @staticmethod
    def dump(obj) -> str:
        return json.dumps(obj, default=str)

    @staticmethod
    def load(raw: str | None):
        if not raw:
            return {}
        return json.loads(raw)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), nullable=False)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    actual_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    deviation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    detection_method: Mapped[str] = mapped_column(String, nullable=False)  # rolling_zscore, iqr
    probable_cause: Mapped[str] = mapped_column(String, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class WasteEvent(Base):
    __tablename__ = "waste_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    zone_id: Mapped[str | None] = mapped_column(String, nullable=True)
    asset_id: Mapped[str | None] = mapped_column(String, nullable=True)
    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), nullable=False)
    rule: Mapped[str] = mapped_column(String, nullable=False)  # e.g. after_hours_hvac
    severity: Mapped[str] = mapped_column(String, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    estimated_waste_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_emissions_kg: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    horizon: Mapped[str] = mapped_column(String, nullable=False)  # 24h, 7d, 30d, 90d
    method: Mapped[str] = mapped_column(String, nullable=False)  # seasonal_naive, holt_winters
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    lower_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    upper_kwh: Mapped[float] = mapped_column(Float, nullable=False)


class OptimizationScenario(Base):
    __tablename__ = "optimization_scenarios"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    objective: Mapped[str] = mapped_column(String, default="balanced")  # cost, energy, emissions, peak, balanced
    parameters_json: Mapped[str] = mapped_column(Text, nullable=False)  # levers applied
    created_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ScenarioResult(Base):
    __tablename__ = "scenario_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("optimization_scenarios.id"), nullable=False)
    baseline_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    scenario_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_cost: Mapped[float] = mapped_column(Float, nullable=False)
    scenario_cost: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_peak_kw: Mapped[float] = mapped_column(Float, nullable=False)
    scenario_peak_kw: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_emissions_kg: Mapped[float] = mapped_column(Float, nullable=False)
    scenario_emissions_kg: Mapped[float] = mapped_column(Float, nullable=False)
    comfort_impact: Mapped[str] = mapped_column(String, default="Low")  # None, Low, Medium, High
    comfort_violations: Mapped[int] = mapped_column(Integer, default=0)
    objective_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String, default="waste_event")  # waste_event, scenario
    source_id: Mapped[str] = mapped_column(String, default="")
    estimated_energy_savings_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost_savings: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_emissions_reduction_kg: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_peak_reduction_kw: Mapped[float] = mapped_column(Float, default=0.0)
    effort: Mapped[str] = mapped_column(String, default="Low")  # Low, Medium, High
    confidence: Mapped[str] = mapped_column(String, default="MEDIUM")  # LOW, MEDIUM, HIGH
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String, default="SUGGESTED"
    )  # SUGGESTED, REVIEWED, APPROVED, REJECTED, MODIFIED, IMPLEMENTED
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    decided_by: Mapped[str] = mapped_column(String, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_reason: Mapped[str] = mapped_column(Text, default="")


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent: Mapped[str] = mapped_column(String, nullable=False)  # energy_analyst, anomaly_analyst, ...
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String, default="MEDIUM")
    limitations: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    provider: Mapped[str] = mapped_column(String, default="mock")
    created_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
