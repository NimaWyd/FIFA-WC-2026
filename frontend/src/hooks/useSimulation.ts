"use client";
import { useEffect, useState } from "react";
import { fetchSimulation } from "@/lib/api";
import type { SimulationResponse } from "@/lib/types";

// Module-level cache so multiple components share one fetch
let _data: SimulationResponse | null = null;
let _inflightPromise: Promise<SimulationResponse> | null = null;
const _listeners: Set<() => void> = new Set();

function notify() {
  _listeners.forEach((fn) => fn());
}

export function useSimulation() {
  const [, rerender] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (_data) return;

    const refresh = () => rerender((n) => n + 1);
    _listeners.add(refresh);

    if (!_inflightPromise) {
      _inflightPromise = fetchSimulation()
        .then((d) => {
          _data = d;
          _inflightPromise = null;
          notify();
          return d;
        })
        .catch((e) => {
          _inflightPromise = null;
          setError(e.message);
          throw e;
        });
    }

    return () => {
      _listeners.delete(refresh);
    };
  }, []);

  return { data: _data, loading: !_data && !error, error };
}
