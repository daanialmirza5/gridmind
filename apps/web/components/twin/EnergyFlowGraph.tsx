"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Edge, Node, Position } from "reactflow";
import "reactflow/dist/style.css";
import { DigitalTwin } from "@/lib/types";

export function EnergyFlowGraph({
  twin,
  currentDemandKw,
  onSelect,
}: {
  twin: DigitalTwin;
  currentDemandKw: number | undefined;
  onSelect: (label: string) => void;
}) {
  const { nodes, edges } = useMemo(() => buildFlow(twin, currentDemandKw), [twin, currentDemandKw]);

  return (
    <div style={{ height: 480 }} className="rounded-lg border border-border overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        onNodeClick={(_, node) => onSelect(String(node.data.label).split("\n")[0])}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#232a35" gap={24} />
      </ReactFlow>
    </div>
  );
}

const CATEGORY_COLORS: Record<string, string> = {
  hvac: "#14202a",
  lighting: "#241f14",
  equipment: "#1a1620",
};

function buildFlow(twin: DigitalTwin, currentDemandKw: number | undefined) {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const style = (bg: string, width = 160) => ({
    background: bg,
    border: "1px solid #232a35",
    borderRadius: 8,
    color: "#e5e9ee",
    fontSize: 11,
    padding: 8,
    width,
    whiteSpace: "pre-line" as const,
  });

  nodes.push({
    id: "grid",
    position: { x: 260, y: 0 },
    data: { label: "GRID" },
    style: { ...style("#0f1a12"), fontWeight: 700, textAlign: "center" as const },
    sourcePosition: Position.Bottom,
  });
  nodes.push({
    id: "main",
    position: { x: 250, y: 110 },
    data: { label: `MAIN METER\n${currentDemandKw ?? "—"} kW` },
    style: { ...style("#1b2a2b"), fontWeight: 600, textAlign: "center" as const },
    targetPosition: Position.Top,
    sourcePosition: Position.Bottom,
  });
  edges.push({ id: "grid-main", source: "grid", target: "main", style: { stroke: "#232a35" } });

  const totals: Record<string, { count: number; ratedKw: number }> = {};
  twin.floors.forEach((f) =>
    f.zones.forEach((z) =>
      z.assets.forEach((a) => {
        totals[a.asset_type] = totals[a.asset_type] || { count: 0, ratedKw: 0 };
        totals[a.asset_type].count += 1;
        totals[a.asset_type].ratedKw += a.rated_power_kw;
      })
    )
  );

  const categories = Object.keys(totals);
  categories.forEach((cat, i) => {
    const id = `cat-${cat}`;
    nodes.push({
      id,
      position: { x: 60 + i * 220, y: 240 },
      data: { label: `${cat.toUpperCase()}\n${totals[cat].count} assets\n~${totals[cat].ratedKw.toFixed(0)} kW rated` },
      style: { ...style(CATEGORY_COLORS[cat] || "#171c24"), textAlign: "center" as const },
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
    });
    edges.push({ id: `main-${id}`, source: "main", target: id, style: { stroke: "#232a35" } });
  });

  let zoneX = 0;
  twin.floors.forEach((f) =>
    f.zones.forEach((z) => {
      const zoneId = `flowzone-${z.id}`;
      const dominantType = z.assets[0]?.asset_type;
      nodes.push({
        id: zoneId,
        position: { x: zoneX, y: 370 },
        data: { label: z.name },
        style: { ...style("#12161c", 140), fontSize: 10 },
        targetPosition: Position.Top,
      });
      if (dominantType) {
        edges.push({
          id: `cat-${dominantType}-${zoneId}`,
          source: `cat-${dominantType}`,
          target: zoneId,
          style: { stroke: "#232a35" },
        });
      }
      zoneX += 150;
    })
  );

  return { nodes, edges };
}
