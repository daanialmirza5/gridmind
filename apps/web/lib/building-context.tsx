"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./api";
import { Building } from "./types";
import { useAuth } from "./auth";

interface BuildingContextValue {
  buildings: Building[];
  buildingId: string;
  setBuildingId: (id: string) => void;
  isLoading: boolean;
}

const BuildingContext = createContext<BuildingContextValue | undefined>(undefined);

export function BuildingProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [buildingId, setBuildingIdState] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["buildings"],
    queryFn: () => apiGet<Building[]>("/api/buildings"),
    enabled: !!user,
  });

  useEffect(() => {
    if (!buildingId && data && data.length > 0) {
      const stored = window.localStorage.getItem("gridmind_building");
      setBuildingIdState(stored && data.some((b) => b.id === stored) ? stored : data[0].id);
    }
  }, [data, buildingId]);

  const setBuildingId = (id: string) => {
    setBuildingIdState(id);
    window.localStorage.setItem("gridmind_building", id);
  };

  return (
    <BuildingContext.Provider value={{ buildings: data || [], buildingId, setBuildingId, isLoading }}>
      {children}
    </BuildingContext.Provider>
  );
}

export function useBuilding() {
  const ctx = useContext(BuildingContext);
  if (!ctx) throw new Error("useBuilding must be used within BuildingProvider");
  return ctx;
}
