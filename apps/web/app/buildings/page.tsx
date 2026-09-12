"use client";

import Link from "next/link";
import { useBuildings } from "@/lib/hooks";
import { Card, QueryBoundary, SectionTitle } from "@/components/ui";

export default function BuildingsPage() {
  const buildings = useBuildings();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Buildings</h1>
      <QueryBoundary isLoading={buildings.isLoading} error={buildings.error} data={buildings.data} empty={(d) => d.length === 0}>
        {(data) => (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.map((b) => (
              <Link key={b.id} href={`/buildings/${b.id}`}>
                <Card className="hover:border-accent transition-colors cursor-pointer">
                  <SectionTitle>{b.name}</SectionTitle>
                  <div className="text-xs text-gray-500 space-y-1">
                    <div>{b.address}</div>
                    <div>{b.area_sqm.toLocaleString()} m²</div>
                    <div className="text-gray-600">{b.id}</div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </QueryBoundary>
    </div>
  );
}
