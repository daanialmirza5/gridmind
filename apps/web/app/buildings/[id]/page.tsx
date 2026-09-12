"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useBuildingDetail, useDigitalTwin, useZone, useAssetHealth } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle, StatTile } from "@/components/ui";
import { DigitalTwinGraph, TwinSelection } from "@/components/twin/DigitalTwinGraph";

export default function BuildingDetailPage() {
  const params = useParams<{ id: string }>();
  const buildingId = params.id;
  const building = useBuildingDetail(buildingId);
  const twin = useDigitalTwin(buildingId);
  const [selection, setSelection] = useState<TwinSelection>(null);

  return (
    <div className="space-y-6">
      <QueryBoundary isLoading={building.isLoading} error={building.error} data={building.data}>
        {(b) => (
          <div>
            <h1 className="text-xl font-bold text-white">{b.name}</h1>
            <p className="text-sm text-gray-500">{b.address}</p>
          </div>
        )}
      </QueryBoundary>

      {building.data?.kpi && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatTile label="Current Power" value={`${building.data.kpi.current_demand_kw ?? "—"} kW`} />
          <StatTile label="Today's Energy" value={`${building.data.kpi.today_energy_kwh ?? "—"} kWh`} />
          <StatTile label="Peak Demand (30d)" value={`${building.data.kpi.peak_demand_kw ?? "—"} kW`} />
          <StatTile label="Area" value={`${building.data.area_sqm.toLocaleString()} m²`} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <SectionTitle>Building Digital Twin</SectionTitle>
          <p className="text-xs text-gray-500 mb-3">Click a floor, zone, or asset to inspect its metrics.</p>
          <QueryBoundary isLoading={twin.isLoading} error={twin.error} data={twin.data}>
            {(t) => <DigitalTwinGraph twin={t} onSelect={setSelection} />}
          </QueryBoundary>
        </Card>

        <Card>
          <SectionTitle>Details</SectionTitle>
          {!selection && <p className="text-xs text-gray-500">Select a node in the twin to see details.</p>}
          {selection?.type === "zone" && <ZoneDetail zoneId={selection.id} />}
          {selection?.type === "asset" && <AssetDetail assetId={selection.id} />}
          {selection?.type === "floor" && <p className="text-sm text-gray-300">{selection.label}</p>}
          {selection?.type === "building" && <p className="text-sm text-gray-300">{selection.label}</p>}
        </Card>
      </div>
    </div>
  );
}

function ZoneDetail({ zoneId }: { zoneId: string }) {
  const zone = useZone(zoneId);
  return (
    <QueryBoundary isLoading={zone.isLoading} error={zone.error} data={zone.data}>
      {(z) => (
        <div className="space-y-2 text-sm">
          <div className="text-white font-medium">{z.name}</div>
          <Row label="Type" value={z.zone_type} />
          <Row label="Area" value={`${z.area_sqm} m²`} />
          <Row label="Max occupancy" value={String(z.max_occupancy)} />
          <Row label="Meters" value={(z.meters || []).join(", ") || "—"} />
          <div className="stat-label mt-3">Assets</div>
          <ul className="text-xs text-gray-400 space-y-1">
            {(z.assets || []).map((a) => (
              <li key={a.id}>
                {a.name} — {a.asset_type} ({a.rated_power_kw} kW rated)
              </li>
            ))}
          </ul>
        </div>
      )}
    </QueryBoundary>
  );
}

function AssetDetail({ assetId }: { assetId: string }) {
  const asset = useAssetHealth(assetId);
  return (
    <QueryBoundary isLoading={asset.isLoading} error={asset.error} data={asset.data}>
      {(a) => (
        <div className="space-y-2 text-sm">
          <div className="text-white font-medium">{a.name}</div>
          <Row label="Type" value={a.asset_type} />
          {a.current_power_kw !== undefined && <Row label="Current power" value={`${a.current_power_kw} kW`} />}
          {a.rated_power_kw !== undefined && <Row label="Rated power" value={`${a.rated_power_kw} kW`} />}
          {a.runtime_hours_7d !== undefined && <Row label="Runtime (7d)" value={`${a.runtime_hours_7d} h`} />}
          {a.heuristic_efficiency_pct !== undefined && <Row label="Efficiency (heuristic)" value={`${a.heuristic_efficiency_pct}%`} />}
          <Row label="Health" value={a.health} />
          {a.health_note && <p className="text-[11px] text-gray-500 italic mt-2">{a.health_note}</p>}
        </div>
      )}
    </QueryBoundary>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-200">{value}</span>
    </div>
  );
}
