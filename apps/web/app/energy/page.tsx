"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useDataQuality, useEnergyPoints } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle } from "@/components/ui";
import { EnergyTrendChart } from "@/components/charts";

const GRANULARITIES = ["hourly", "daily", "weekly", "monthly"] as const;

export default function EnergyPage() {
  const { buildingId } = useBuilding();
  const [granularity, setGranularity] = useState<(typeof GRANULARITIES)[number]>("daily");
  const energy = useEnergyPoints(buildingId, granularity);
  const quality = useDataQuality(buildingId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Energy Consumption Analytics</h1>
        <div className="flex gap-1">
          {GRANULARITIES.map((g) => (
            <button
              key={g}
              onClick={() => setGranularity(g)}
              className={`text-xs px-3 py-1.5 rounded-md border ${
                granularity === g ? "border-accent text-accent" : "border-border text-gray-400"
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      <Card>
        <SectionTitle>Consumption Trend ({granularity})</SectionTitle>
        <QueryBoundary isLoading={energy.isLoading} error={energy.error} data={energy.data} empty={(d) => d.points.length === 0}>
          {(d) => <EnergyTrendChart points={d.points} />}
        </QueryBoundary>
      </Card>

      <Card>
        <SectionTitle>Data Quality</SectionTitle>
        <QueryBoundary isLoading={quality.isLoading} error={quality.error} data={quality.data}>
          {(q) => (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 text-sm">
              <Metric label="Readings" value={q.total_readings} />
              <Metric label="Valid" value={q.valid_readings} tone="good" />
              <Metric label="Missing intervals" value={q.missing_intervals} tone="warn" />
              <Metric label="Duplicates" value={q.duplicate_readings} tone="warn" />
              <Metric label="Suspicious" value={q.suspicious_readings} tone="warn" />
              <Metric label="Negative" value={q.negative_readings} tone="bad" />
              <Metric label="Stale sensor" value={q.stale_sensor_readings} tone="warn" />
            </div>
          )}
        </QueryBoundary>
        <p className="text-[11px] text-gray-500 mt-3">
          These counts are computed directly from the energy ledger and the most recent CSV/JSON import job — see{" "}
          <span className="text-gray-400">docs/model_cards.md</span> for methodology.
        </p>
      </Card>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone?: "good" | "warn" | "bad" }) {
  const color = tone === "good" ? "text-emerald-400" : tone === "warn" ? "text-amber-400" : tone === "bad" ? "text-red-400" : "text-gray-100";
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`text-lg font-semibold ${value > 0 && tone ? color : "text-gray-100"}`}>{value.toLocaleString()}</div>
    </div>
  );
}
