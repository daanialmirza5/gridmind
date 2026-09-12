"use client";

import { useParams } from "next/navigation";
import { useZone } from "@/lib/hooks";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { Anomaly, EnergyPoint } from "@/lib/types";
import { Card, QueryBoundary, SectionTitle } from "@/components/ui";
import { EnergyTrendChart } from "@/components/charts";

export default function ZoneDetailPage() {
  const params = useParams<{ id: string }>();
  const zoneId = params.id;
  const zone = useZone(zoneId);

  const energy = useQuery({
    queryKey: ["zone-energy", zoneId],
    queryFn: () => apiGet<{ points: EnergyPoint[] }>("/api/energy", { zone_id: zoneId, granularity: "daily" }),
  });

  const anomalies = useQuery({
    queryKey: ["zone-anomalies", zoneId],
    queryFn: () => apiGet<Anomaly[]>("/api/anomalies", { limit: 200 }).then((rows) => rows),
  });

  return (
    <div className="space-y-4">
      <QueryBoundary isLoading={zone.isLoading} error={zone.error} data={zone.data}>
        {(z) => (
          <div>
            <h1 className="text-xl font-bold text-white">{z.name}</h1>
            <p className="text-sm text-gray-500">
              {z.zone_type} · {z.area_sqm} m² · max occupancy {z.max_occupancy}
            </p>
          </div>
        )}
      </QueryBoundary>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <SectionTitle>Energy</SectionTitle>
          <QueryBoundary isLoading={energy.isLoading} error={energy.error} data={energy.data} empty={(d) => d.points.length === 0}>
            {(d) => <EnergyTrendChart points={d.points} />}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionTitle>Assets</SectionTitle>
          <QueryBoundary isLoading={zone.isLoading} error={zone.error} data={zone.data?.assets} empty={(d) => d.length === 0}>
            {(assets) => (
              <ul className="text-sm space-y-2">
                {assets.map((a) => (
                  <li key={a.id} className="flex justify-between text-xs border-b border-border pb-1.5 last:border-0">
                    <span className="text-gray-200">{a.name}</span>
                    <span className="text-gray-500">
                      {a.asset_type} · {a.rated_power_kw} kW
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </QueryBoundary>
        </Card>
      </div>

      <Card>
        <SectionTitle>Recent Anomalies (this building)</SectionTitle>
        <p className="text-[11px] text-gray-500 mb-2">
          Anomalies are tracked per meter, not per zone; showing the building&apos;s recent anomalies for context.
        </p>
        <QueryBoundary
          isLoading={anomalies.isLoading}
          error={anomalies.error}
          data={(anomalies.data || []).slice(0, 10)}
          empty={(d) => d.length === 0}
        >
          {(rows) => (
            <ul className="text-xs space-y-1">
              {rows.map((a) => (
                <li key={a.id} className="text-gray-400">
                  {a.meter_id} — {a.severity} — {new Date(a.timestamp).toLocaleString()}
                </li>
              ))}
            </ul>
          )}
        </QueryBoundary>
      </Card>
    </div>
  );
}
