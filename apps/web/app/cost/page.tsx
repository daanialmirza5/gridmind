"use client";

import { useBuilding } from "@/lib/building-context";
import { useCost } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle, StatTile } from "@/components/ui";

export default function CostPage() {
  const { buildingId } = useBuilding();
  const cost = useCost(buildingId);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Cost Intelligence</h1>
      <QueryBoundary isLoading={cost.isLoading} error={cost.error} data={cost.data}>
        {(c) => (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatTile label="Consumption Cost" value={`$${c.consumption_cost.toLocaleString()}`} />
              <StatTile label="Peak Cost" value={`$${c.peak_cost.toLocaleString()}`} />
              <StatTile label="Demand Cost" value={`$${c.demand_cost.toLocaleString()}`} />
              <StatTile label="Total Estimated Cost" value={`$${c.total_cost.toLocaleString()}`} tone="warn" />
            </div>
            <Card>
              <SectionTitle>Tariff: {c.tariff_name}</SectionTitle>
              <p className="text-xs text-gray-400">
                Type: {c.tariff_type.replace(/_/g, " ")}. {c.is_synthetic_assumption && "This tariff is a clearly-labeled demo assumption, not a real utility rate."}
              </p>
            </Card>
          </>
        )}
      </QueryBoundary>
    </div>
  );
}
