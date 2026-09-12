export interface Building {
  id: string;
  organization_id: string;
  name: string;
  address: string;
  area_sqm: number;
  timezone: string;
  kpi?: KpiSummary;
  eui?: EuiResult;
}

export interface KpiSummary {
  as_of?: string;
  today_energy_kwh?: number;
  month_energy_kwh?: number;
  current_demand_kw?: number;
  peak_demand_kw?: number;
}

export interface EuiResult {
  current_eui_kwh_per_sqm: number;
  current_eui_kwh_per_sqft: number;
  previous_eui_kwh_per_sqm: number | null;
  change_pct: number | null;
}

export interface Zone {
  id: string;
  floor_id: string;
  name: string;
  zone_type: string;
  area_sqm: number;
  max_occupancy: number;
  assets?: { id: string; name: string; asset_type: string; rated_power_kw: number }[];
  meters?: string[];
}

export interface TwinAsset {
  id: string;
  name: string;
  asset_type: string;
  rated_power_kw: number;
  install_year: number;
  meters: string[];
}

export interface TwinZone {
  id: string;
  name: string;
  zone_type: string;
  area_sqm: number;
  max_occupancy: number;
  meters: string[];
  assets: TwinAsset[];
}

export interface TwinFloor {
  id: string;
  name: string;
  level: number;
  zones: TwinZone[];
}

export interface DigitalTwin {
  building: Building;
  main_meter_id: string | null;
  floors: TwinFloor[];
}

export interface EnergyPoint {
  timestamp: string;
  energy_kwh: number;
  peak_power_kw: number;
  avg_temperature_c: number | null;
  avg_occupancy: number | null;
}

export interface DataQualityReport {
  scope: string;
  total_readings: number;
  valid_readings: number;
  missing_intervals: number;
  duplicate_readings: number;
  suspicious_readings: number;
  negative_readings: number;
  stale_sensor_readings: number;
}

export interface Anomaly {
  id: string;
  meter_id: string;
  building_id: string;
  timestamp: string;
  expected_kwh: number;
  actual_kwh: number;
  deviation_pct: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  detection_method: string;
  probable_cause: string;
  evidence: Record<string, unknown>;
}

export interface WasteEvent {
  id: string;
  building_id: string;
  zone_id: string | null;
  asset_id: string | null;
  meter_id: string;
  rule: string;
  severity: string;
  window_start: string;
  window_end: string;
  estimated_waste_kwh: number;
  estimated_cost: number;
  estimated_emissions_kg: number;
  evidence: Record<string, unknown>;
}

export interface ForecastPoint {
  timestamp: string;
  expected_kwh: number;
  lower_kwh: number;
  upper_kwh: number;
}

export interface ForecastResponse {
  building_id: string;
  horizon: string;
  method: string;
  points: ForecastPoint[];
}

export interface PeakPrediction {
  building_id: string;
  expected_peak_timestamp: string;
  expected_peak_kw: number;
  historical_peak_kw: number;
  risk: "LOW" | "MEDIUM" | "HIGH";
}

export interface ForecastEvaluation {
  horizon_label: string;
  horizon_hours: number;
  method: string;
  mae: number;
  rmse: number;
  mape: number;
  n_points: number;
}

export interface ScenarioMetrics {
  baseline_energy_kwh: number;
  scenario_energy_kwh: number;
  baseline_cost: number;
  scenario_cost: number;
  baseline_peak_kw: number;
  scenario_peak_kw: number;
  baseline_emissions_kg: number;
  scenario_emissions_kg: number;
  energy_change_pct: number;
  cost_change_pct: number;
  peak_change_pct: number;
  emissions_change_pct: number;
}

export interface ScenarioSimulation {
  building_id: string;
  levers: Record<string, number>;
  objective: string;
  metrics: ScenarioMetrics;
  comfort_impact: string;
  comfort_violations: number;
  comfort_notes: string[];
  objective_score: number;
}

export interface Scenario {
  id: string;
  building_id: string;
  name: string;
  objective: string;
  parameters: Record<string, number>;
  created_by: string;
  created_at: string;
  result?: {
    energy_change_pct: number | null;
    cost_change_pct: number | null;
    comfort_impact: string | null;
    objective_score: number | null;
  } | null;
}

export interface Recommendation {
  id: string;
  building_id: string;
  title: string;
  description: string;
  source_type: string;
  source_id: string;
  estimated_energy_savings_kwh: number;
  estimated_cost_savings: number;
  estimated_emissions_reduction_kg: number;
  estimated_peak_reduction_kw: number;
  effort: string;
  confidence: string;
  priority_score: number;
  status: string;
  evidence: Record<string, unknown>;
  created_at: string;
  decided_by: string;
  decided_at: string | null;
  decision_reason: string;
  disclaimer: string;
}

export interface CarbonResult {
  building_id: string | null;
  total_kg_co2e: number;
  factor_used: number;
  factor_source: string;
  factor_region: string;
  is_synthetic_assumption: boolean;
}

export interface CostResult {
  building_id: string;
  tariff_name: string;
  tariff_type: string;
  currency: string;
  consumption_cost: number;
  peak_cost: number;
  off_peak_cost: number;
  demand_cost: number;
  total_cost: number;
  is_synthetic_assumption: boolean;
}

export interface AiAnalysis {
  id: string;
  agent: string;
  question: string;
  answer: string;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  limitations: string;
  evidence: Record<string, unknown>;
  provider: string;
  created_at: string;
}

export interface AuditEvent {
  id: number;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  previous_state: string;
  new_state: string;
  reason: string;
  timestamp: string;
}

export interface Notification {
  id: number;
  building_id: string;
  notification_type: string;
  severity: string;
  title: string;
  message: string;
  entity_type: string;
  entity_id: string;
  is_read: boolean;
  created_at: string;
}

export interface SystemHealth {
  database: string;
  meters_registered: number;
  last_successful_ingestion: string | null;
  ai_provider_configured: string;
  environment: string;
}

export interface ReplaySnapshot {
  building_id: string;
  timestamp: string;
  temperature_c: number | null;
  main_power_kw: number | null;
  zones: {
    zone_id: string;
    meter_id: string;
    power_kw: number;
    occupancy: number | null;
    operating_state: string;
  }[];
}

export interface AssetHealth {
  id: string;
  name: string;
  asset_type: string;
  rated_power_kw?: number;
  install_year?: number;
  current_power_kw?: number;
  avg_power_kw_7d?: number;
  runtime_hours_7d?: number;
  heuristic_efficiency_pct?: number;
  health: string;
  health_is_heuristic?: boolean;
  health_note?: string;
}
