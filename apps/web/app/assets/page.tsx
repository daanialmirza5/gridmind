"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useDigitalTwin, useAssetHealth } from "@/lib/hooks";
import { Badge, Card, QueryBoundary, SectionTitle } from "@/components/ui";

interface AssetRow {
  id: string;
  zone_id: string;
  name: string;
  asset_type: string;
  rated_power_kw: number;
  install_year: number;
}

export default function AssetsPage() {
  const { buildingId } = useBuilding();
  const twin = useDigitalTwin(buildingId);
  const [selected, setSelected] = useState<string | null>(null);

  const assets: AssetRow[] =
    twin.data?.floors.flatMap((f) => f.zones.flatMap((z) => z.assets.map((a) => ({ ...a, zone_id: z.id })))) || [];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Assets</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 overflow-x-auto">
          <SectionTitle>All Assets</SectionTitle>
          <QueryBoundary isLoading={twin.isLoading} error={twin.error} data={assets} empty={(d) => d.length === 0}>
            {(rows) => (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-border">
                    <th className="py-2">Asset</th>
                    <th>Type</th>
                    <th>Rated (kW)</th>
                    <th>Install Year</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((a) => (
                    <tr
                      key={a.id}
                      onClick={() => setSelected(a.id)}
                      className={`border-b border-border/50 cursor-pointer hover:bg-white/5 ${
                        selected === a.id ? "bg-white/5" : ""
                      }`}
                    >
                      <td className="py-2 text-gray-200">{a.name}</td>
                      <td className="text-gray-400">{a.asset_type}</td>
                      <td className="text-gray-400">{a.rated_power_kw}</td>
                      <td className="text-gray-400">{a.install_year}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionTitle>Asset Health</SectionTitle>
          {selected ? <AssetHealthPanel assetId={selected} /> : <p className="text-xs text-gray-500">Select an asset.</p>}
        </Card>
      </div>
    </div>
  );
}

function AssetHealthPanel({ assetId }: { assetId: string }) {
  const health = useAssetHealth(assetId);
  return (
    <QueryBoundary isLoading={health.isLoading} error={health.error} data={health.data}>
      {(a) => (
        <div className="space-y-2 text-sm">
          <div className="text-white font-medium">{a.name}</div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Health</span>
            <Badge tone={a.health === "GOOD" ? "good" : a.health === "FAIR" ? "MEDIUM" : "HIGH"}>{a.health}</Badge>
          </div>
          {a.current_power_kw !== undefined && <Detail label="Current power" value={`${a.current_power_kw} kW`} />}
          {a.avg_power_kw_7d !== undefined && <Detail label="Avg power (7d)" value={`${a.avg_power_kw_7d} kW`} />}
          {a.runtime_hours_7d !== undefined && <Detail label="Runtime (7d)" value={`${a.runtime_hours_7d} h`} />}
          {a.heuristic_efficiency_pct !== undefined && (
            <Detail label="Heuristic efficiency" value={`${a.heuristic_efficiency_pct}%`} />
          )}
          {a.health_note && <p className="text-[11px] text-gray-500 italic mt-2">{a.health_note}</p>}
        </div>
      )}
    </QueryBoundary>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-200">{value}</span>
    </div>
  );
}
