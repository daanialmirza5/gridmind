"use client";

import { useBuilding } from "@/lib/building-context";
import { useCarbon } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle, StatTile } from "@/components/ui";

export default function CarbonPage() {
  const { buildingId } = useBuilding();
  const carbon = useCarbon(buildingId);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Carbon Intelligence</h1>
      <QueryBoundary isLoading={carbon.isLoading} error={carbon.error} data={carbon.data}>
        {(c) => (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <StatTile label="Total Emissions" value={`${c.total_kg_co2e.toLocaleString()} kg CO2e`} />
              <StatTile label="Emission Factor" value={`${c.factor_used} kgCO2e/kWh`} />
              <StatTile label="Source / Region" value={`${c.factor_source} / ${c.factor_region}`} />
            </div>
            <Card>
              <SectionTitle>Methodology</SectionTitle>
              <p className="text-xs text-gray-400">
                CO2e = total metered energy consumption × emission factor. The factor above is a{" "}
                {c.is_synthetic_assumption ? "clearly-labeled demo assumption" : "configured value"}, not an official
                government or utility figure. See docs/model_cards.md for full methodology.
              </p>
            </Card>
          </>
        )}
      </QueryBoundary>
    </div>
  );
}
