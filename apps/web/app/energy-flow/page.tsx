"use client";

import { useState } from "react";
import { useBuilding } from "@/lib/building-context";
import { useBuildingDetail, useDigitalTwin } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle } from "@/components/ui";
import { EnergyFlowGraph } from "@/components/twin/EnergyFlowGraph";

export default function EnergyFlowPage() {
  const { buildingId } = useBuilding();
  const twin = useDigitalTwin(buildingId);
  const building = useBuildingDetail(buildingId);
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Energy Flow</h1>
      <p className="text-sm text-gray-500">GRID → Main Meter → Asset Category → Zone. Click a node to select it.</p>

      <Card>
        <SectionTitle>{selected ? `Selected: ${selected}` : "Flow Diagram"}</SectionTitle>
        <QueryBoundary isLoading={twin.isLoading} error={twin.error} data={twin.data}>
          {(t) => (
            <EnergyFlowGraph twin={t} currentDemandKw={building.data?.kpi?.current_demand_kw} onSelect={setSelected} />
          )}
        </QueryBoundary>
      </Card>
    </div>
  );
}
