"use client";
import { useEffect, useState } from "react";
import { fetchSimulation } from "@/lib/api";
import type { SimulationResponse } from "@/lib/types";

export function useSimulation() {
  const [data, setData] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchSimulation()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
