"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Edge, Node, Position } from "reactflow";
import "reactflow/dist/style.css";
import { DigitalTwin } from "@/lib/types";

const NODE_W = 170;
const ASSET_W = 130;
const H_GAP = 20;
const LEVEL_H = 110;

export type TwinSelection = { type: "building" | "floor" | "zone" | "asset"; id: string; label: string } | null;

export function DigitalTwinGraph({
  twin,
  onSelect,
}: {
  twin: DigitalTwin;
  onSelect: (sel: TwinSelection) => void;
}) {
  const { nodes, edges } = useMemo(() => buildGraph(twin), [twin]);

  return (
    <div style={{ height: 560 }} className="rounded-lg border border-border overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        onNodeClick={(_, node) => onSelect(node.data.selection)}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#232a35" gap={24} />
      </ReactFlow>
    </div>
  );
}

function buildGraph(twin: DigitalTwin): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const style = (bg: string) => ({
    background: bg,
    border: "1px solid #232a35",
    borderRadius: 8,
    color: "#e5e9ee",
    fontSize: 11,
    padding: 8,
    width: NODE_W,
  });

  let cursorX = 0;
  const buildingId = `building-${twin.building.id}`;
  nodes.push({
    id: buildingId,
    position: { x: 0, y: 0 },
    data: {
      label: twin.building.name,
      selection: { type: "building", id: twin.building.id, label: twin.building.name },
    },
    style: { ...style("#1b2a2b"), width: NODE_W + 40, fontWeight: 600 },
    sourcePosition: Position.Bottom,
  });

  twin.floors.forEach((floor) => {
    const floorStartX = cursorX;
    const floorId = `floor-${floor.id}`;

    floor.zones.forEach((zone) => {
      const zoneId = `zone-${zone.id}`;
      const zoneX = cursorX;
      nodes.push({
        id: zoneId,
        position: { x: zoneX, y: LEVEL_H * 2 },
        data: { label: `${zone.name}\n${zone.zone_type}`, selection: { type: "zone", id: zone.id, label: zone.name } },
        style: style("#14202a"),
        targetPosition: Position.Top,
        sourcePosition: Position.Bottom,
      });
      edges.push({ id: `${floorId}-${zoneId}`, source: floorId, target: zoneId, style: { stroke: "#232a35" } });

      zone.assets.forEach((asset, ai) => {
        const assetId = `asset-${asset.id}`;
        nodes.push({
          id: assetId,
          position: { x: zoneX + ai * (ASSET_W + 10), y: LEVEL_H * 3 },
          data: {
            label: `${asset.name}\n${asset.asset_type}`,
            selection: { type: "asset", id: asset.id, label: asset.name },
          },
          style: { ...style("#1a1620"), width: ASSET_W },
          targetPosition: Position.Top,
        });
        edges.push({ id: `${zoneId}-${assetId}`, source: zoneId, target: assetId, style: { stroke: "#232a35" } });
      });

      cursorX += NODE_W + H_GAP;
    });

    const floorWidth = cursorX - floorStartX - H_GAP;
    nodes.push({
      id: floorId,
      position: { x: floorStartX + floorWidth / 2 - NODE_W / 2, y: LEVEL_H },
      data: { label: floor.name, selection: { type: "floor", id: floor.id, label: floor.name } },
      style: style("#171c24"),
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
    });
    edges.push({ id: `${buildingId}-${floorId}`, source: buildingId, target: floorId, style: { stroke: "#232a35" } });

    cursorX += H_GAP * 2;
  });

  return { nodes, edges };
}
