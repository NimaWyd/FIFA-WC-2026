"use client";
import { useEffect, useState } from "react";
import { fetchSimulation } from "@/lib/api";
import type { SimulationResponse } from "@/lib/types";
import { getCached, setCached, isStale } from "@/lib/localCache";

const CACHE_KEY = "simulation_v1";

// Module-level cache: survives component unmount/remount within the same session.
// Populated from localStorage on first access so page-refresh is also instant.
let _data: SimulationResponse | null = null;
let _inflightPromise: Promise<SimulationResponse> | null = null;
const _listeners: Set<() => void> = new Set();

function _notify() {
  _listeners.forEach((fn) => fn());
}

// Called synchronously before first render — reads localStorage into _data
// so every component mounting in the same render cycle gets data immediately.
function _hydrateFromStorage() {
  if (_data) return;
  const cached = getCached<SimulationResponse>(CACHE_KEY);
  if (cached) _data = cached;
}

function _fetchFresh() {
  if (_inflightPromise) return;
  _inflightPromise = fetchSimulation()
    .then((d) => {
      _data = d;
      setCached(CACHE_KEY, d);
      _inflightPromise = null;
      _notify();
      return d;
    })
    .catch((e) => {
      _inflightPromise = null;
      _notify(); // trigger rerender so error is surfaced
      throw e;
    });
}

export function useSimulation() {
  _hydrateFromStorage();

  const [, rerender] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => rerender((n) => n + 1);
    _listeners.add(refresh);

    // Fetch fresh if: no data at all, or data is stale (>48 min old)
    if (!_data || isStale(CACHE_KEY)) {
      try {
        _fetchFresh();
      } catch (e: unknown) {
        if (!_data) setError(e instanceof Error ? e.message : "Failed to load simulation");
      }
    }

    return () => { _listeners.delete(refresh); };
  }, []);

  return { data: _data, loading: !_data && !error, error };
}
