"use client";

import Link from "next/link";
import { useBuilding } from "@/lib/building-context";
import {
  useAnomalies,
  useBuildingDetail,
  useEnergyPoints,
  useForecast,
  useRecommendations,
  useSystemHealth,
  useWasteEvents,
} from "@/lib/hooks";
import { Badge, Card, QueryBoundary, SectionTitle, StatTile } from "@/components/ui";
import { EnergyTrendChart, ForecastChart } from "@/components/charts";

export default function DashboardPage() {
  const { buildingId } = useBuilding();
  const building = useBuildingDetail(buildingId);
  const energy = useEnergyPoints(buildingId, "hourly");
  const forecast = useForecast(buildingId, "24h");
  const anomalies = useAnomalies(buildingId);
  const waste = useWasteEvents(buildingId);
  const recs = useRecommendations(buildingId, "SUGGESTED");
  const health = useSystemHealth();

  if (!buildingId) return null;

  const kpi = building.data?.kpi;
  const topWaste = [...(waste.data || [])].sort((a, b) => b.estimated_cost - a.estimated_cost).slice(0, 5);
  const topRecs = [...(recs.data || [])].sort((a, b) => b.priority_score - a.priority_score).slice(0, 5);
  const recentAnomalies = (anomalies.data || []).slice(0, 6);
  const totalPotentialSavings = (recs.data || []).reduce((sum, r) => sum + r.estimated_cost_savings, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Energy Command Center</h1>
        <p className="text-sm text-gray-500">{building.data?.name}</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatTile label="Today's Energy" value={fmt(kpi?.today_energy_kwh, "kWh")} />
        <StatTile label="Current Demand" value={fmt(kpi?.current_demand_kw, "kW")} />
        <StatTile label="Monthly Consumption" value={fmt(kpi?.month_energy_kwh, "kWh")} />
        <StatTile label="Peak Demand (30d)" value={fmt(kpi?.peak_demand_kw, "kW")} />
        <StatTile
          label="Active Anomalies"
          value={anomalies.data?.length ?? "—"}
          tone={anomalies.data && anomalies.data.length > 0 ? "warn" : "good"}
        />
        <StatTile
          label="Potential Savings"
          value={`$${totalPotentialSavings.toFixed(0)}`}
          sub="from open recommendations"
          tone="good"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <SectionTitle action={<Link href="/energy" className="text-xs text-accent">View energy →</Link>}>
            Consumption Trend
          </SectionTitle>
          <QueryBoundary isLoading={energy.isLoading} error={energy.error} data={energy.data} empty={(d) => d.points.length === 0}>
            {(d) => <EnergyTrendChart points={d.points} />}
          </QueryBoundary>
        </Card>
        <Card>
          <SectionTitle action={<Link href="/forecast" className="text-xs text-accent">View forecast →</Link>}>
            24h Forecast
          </SectionTitle>
          <QueryBoundary isLoading={forecast.isLoading} error={forecast.error} data={forecast.data} empty={(d) => d.points.length === 0}>
            {(d) => <ForecastChart points={d.points} />}
          </QueryBoundary>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <SectionTitle action={<Link href="/anomalies" className="text-xs text-accent">View all →</Link>}>
            Anomaly Timeline
          </SectionTitle>
          <QueryBoundary isLoading={anomalies.isLoading} error={anomalies.error} data={recentAnomalies} empty={(d) => d.length === 0}>
            {(d) => (
              <ul className="space-y-2">
                {d.map((a) => (
                  <li key={a.id} className="text-xs border-b border-border pb-2 last:border-0">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-300">{a.meter_id}</span>
                      <Badge tone={a.severity}>{a.severity}</Badge>
                    </div>
                    <div className="text-gray-500 mt-0.5">
                      {a.actual_kwh} kWh vs {a.expected_kwh} expected ({a.deviation_pct > 0 ? "+" : ""}
                      {a.deviation_pct}%)
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionTitle action={<Link href="/waste" className="text-xs text-accent">View all →</Link>}>
            Top Waste Events
          </SectionTitle>
          <QueryBoundary isLoading={waste.isLoading} error={waste.error} data={topWaste} empty={(d) => d.length === 0}>
            {(d) => (
              <ul className="space-y-2">
                {d.map((w) => (
                  <li key={w.id} className="text-xs border-b border-border pb-2 last:border-0">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-300">{w.rule.replace(/_/g, " ")}</span>
                      <Badge tone={w.severity}>{w.severity}</Badge>
                    </div>
                    <div className="text-gray-500 mt-0.5">
                      {w.estimated_waste_kwh} kWh (~${w.estimated_cost})
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionTitle action={<Link href="/recommendations" className="text-xs text-accent">View all →</Link>}>
            Top Opportunities
          </SectionTitle>
          <QueryBoundary isLoading={recs.isLoading} error={recs.error} data={topRecs} empty={(d) => d.length === 0}>
            {(d) => (
              <ul className="space-y-2">
                {d.map((r, i) => (
                  <li key={r.id} className="text-xs border-b border-border pb-2 last:border-0">
                    <div className="text-gray-300">
                      {i + 1}. {r.title}
                    </div>
                    <div className="text-gray-500 mt-0.5">
                      ${r.estimated_cost_savings} savings · {r.effort} effort · {r.confidence} confidence
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </QueryBoundary>
        </Card>
      </div>

      <Card>
        <SectionTitle>System Health</SectionTitle>
        <QueryBoundary isLoading={health.isLoading} error={health.error} data={health.data}>
          {(d) => (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <HealthItem label="Database" value={d.database} good={d.database === "OK"} />
              <HealthItem label="Meters Registered" value={String(d.meters_registered)} good />
              <HealthItem label="AI Provider" value={d.ai_provider_configured} good />
              <HealthItem
                label="Last Ingestion"
                value={d.last_successful_ingestion ? new Date(d.last_successful_ingestion).toLocaleString() : "—"}
                good={!!d.last_successful_ingestion}
              />
            </div>
          )}
        </QueryBoundary>
      </Card>
    </div>
  );
}

function fmt(value: number | undefined, unit: string) {
  if (value === undefined || value === null) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unit}`;
}

function HealthItem({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={good ? "text-emerald-400" : "text-red-400"}>{value}</div>
    </div>
  );
}
