"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "./api";
import {
  AiAnalysis,
  Anomaly,
  AssetHealth,
  AuditEvent,
  Building,
  CarbonResult,
  CostResult,
  DataQualityReport,
  DigitalTwin,
  EnergyPoint,
  ForecastEvaluation,
  ForecastResponse,
  Notification,
  PeakPrediction,
  Recommendation,
  ReplaySnapshot,
  Scenario,
  ScenarioSimulation,
  SystemHealth,
  WasteEvent,
  Zone,
} from "./types";

export function useBuildings() {
  return useQuery({ queryKey: ["buildings"], queryFn: () => apiGet<Building[]>("/api/buildings") });
}

export function useBuildingDetail(buildingId: string) {
  return useQuery({
    queryKey: ["building", buildingId],
    queryFn: () => apiGet<Building>(`/api/buildings/${buildingId}`),
    enabled: !!buildingId,
  });
}

export function useDigitalTwin(buildingId: string) {
  return useQuery({
    queryKey: ["twin", buildingId],
    queryFn: () => apiGet<DigitalTwin>(`/api/buildings/${buildingId}/twin`),
    enabled: !!buildingId,
  });
}

export function useZone(zoneId: string | undefined) {
  return useQuery({
    queryKey: ["zone", zoneId],
    queryFn: () => apiGet<Zone>(`/api/zones/${zoneId}`),
    enabled: !!zoneId,
  });
}

export function useAssetHealth(assetId: string | undefined) {
  return useQuery({
    queryKey: ["asset-health", assetId],
    queryFn: () => apiGet<AssetHealth>(`/api/assets/${assetId}`),
    enabled: !!assetId,
  });
}

export function useEnergySummary(buildingId: string) {
  return useQuery({
    queryKey: ["energy-summary", buildingId],
    queryFn: () => apiGet(`/api/energy/summary`, { building_id: buildingId }),
    enabled: !!buildingId,
    refetchInterval: 60_000,
  });
}

export function useEnergyPoints(buildingId: string, granularity: string) {
  return useQuery({
    queryKey: ["energy-points", buildingId, granularity],
    queryFn: () =>
      apiGet<{ granularity: string; points: EnergyPoint[] }>("/api/energy", {
        building_id: buildingId,
        granularity,
      }),
    enabled: !!buildingId,
  });
}

export function useDataQuality(buildingId?: string) {
  return useQuery({
    queryKey: ["data-quality", buildingId],
    queryFn: () => apiGet<DataQualityReport>("/api/energy/quality", { building_id: buildingId }),
  });
}

export function useAnomalies(buildingId: string, severity?: string) {
  return useQuery({
    queryKey: ["anomalies", buildingId, severity],
    queryFn: () => apiGet<Anomaly[]>("/api/anomalies", { building_id: buildingId, severity, limit: 100 }),
    enabled: !!buildingId,
  });
}

export function useWasteEvents(buildingId: string) {
  return useQuery({
    queryKey: ["waste-events", buildingId],
    queryFn: () => apiGet<WasteEvent[]>("/api/waste-events", { building_id: buildingId, limit: 100 }),
    enabled: !!buildingId,
  });
}

export function useForecast(buildingId: string, horizon: string) {
  return useQuery({
    queryKey: ["forecast", buildingId, horizon],
    queryFn: () => apiGet<ForecastResponse>("/api/forecasts", { building_id: buildingId, horizon }),
    enabled: !!buildingId,
  });
}

export function usePeakPrediction(buildingId: string) {
  return useQuery({
    queryKey: ["peak-prediction", buildingId],
    queryFn: () => apiGet<PeakPrediction>("/api/forecasts/peak", { building_id: buildingId }),
    enabled: !!buildingId,
  });
}

export function useForecastEvaluation(buildingId: string) {
  return useQuery({
    queryKey: ["forecast-eval", buildingId],
    queryFn: () => apiGet<{ building_id: string; evaluations: ForecastEvaluation[] }>("/api/forecasts/evaluation", {
      building_id: buildingId,
    }),
    enabled: !!buildingId,
  });
}

export function useScenarios(buildingId: string) {
  return useQuery({
    queryKey: ["scenarios", buildingId],
    queryFn: () => apiGet<Scenario[]>("/api/scenarios", { building_id: buildingId }),
    enabled: !!buildingId,
  });
}

export function useSimulateScenario() {
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiPost<ScenarioSimulation>("/api/scenarios/simulate", payload),
  });
}

export function useCreateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiPost("/api/scenarios", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenarios"] }),
  });
}

export function useRecommendations(buildingId: string, status?: string) {
  return useQuery({
    queryKey: ["recommendations", buildingId, status],
    queryFn: () => apiGet<Recommendation[]>("/api/recommendations", { building_id: buildingId, status }),
    enabled: !!buildingId,
  });
}

export function useDecideRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, reason }: { id: string; action: "approve" | "reject" | "implement"; reason: string }) =>
      apiPost<Recommendation>(`/api/recommendations/${id}/${action}`, { reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recommendations"] });
      qc.invalidateQueries({ queryKey: ["audit"] });
    },
  });
}

export function useCarbon(buildingId: string) {
  return useQuery({
    queryKey: ["carbon", buildingId],
    queryFn: () => apiGet<CarbonResult>("/api/carbon", { building_id: buildingId }),
    enabled: !!buildingId,
  });
}

export function useCost(buildingId: string) {
  return useQuery({
    queryKey: ["cost", buildingId],
    queryFn: () => apiGet<CostResult>("/api/cost", { building_id: buildingId }),
    enabled: !!buildingId,
  });
}

export function useAskAi() {
  return useMutation({
    mutationFn: (payload: { question: string; building_id: string }) => apiPost<AiAnalysis>("/api/ai/analyze", payload),
  });
}

export function useAiHistory(buildingId: string) {
  return useQuery({
    queryKey: ["ai-history", buildingId],
    queryFn: () => apiGet<AiAnalysis[]>("/api/ai/history", { building_id: buildingId }),
    enabled: !!buildingId,
  });
}

export function useAuditEvents(entityType?: string) {
  return useQuery({
    queryKey: ["audit", entityType],
    queryFn: () => apiGet<AuditEvent[]>("/api/audit", { entity_type: entityType, limit: 100 }),
  });
}

export function useSystemHealth() {
  return useQuery({
    queryKey: ["system-health"],
    queryFn: () => apiGet<SystemHealth>("/api/system-health"),
    refetchInterval: 30_000,
  });
}

export function useNotifications(buildingId?: string) {
  return useQuery({
    queryKey: ["notifications", buildingId],
    queryFn: () => apiGet<Notification[]>("/api/notifications", { building_id: buildingId }),
    refetchInterval: 30_000,
  });
}

export function useReplay(buildingId: string, at: string) {
  return useQuery({
    queryKey: ["replay", buildingId, at],
    queryFn: () => apiGet<ReplaySnapshot>(`/api/buildings/${buildingId}/replay`, { at }),
    enabled: !!buildingId && !!at,
  });
}
