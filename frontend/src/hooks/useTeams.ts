"use client";
import { useEffect, useState } from "react";
import { fetchTeams } from "@/lib/api";
import type { TeamInfo } from "@/lib/types";
import { getCached, setCached, isStale } from "@/lib/localCache";

const CACHE_KEY = "teams_v1";

let _data: TeamInfo[] | null = null;
let _inflightPromise: Promise<TeamInfo[]> | null = null;
const _listeners: Set<() => void> = new Set();

function _notify() {
  _listeners.forEach((fn) => fn());
}

function _hydrateFromStorage() {
  if (_data) return;
  const cached = getCached<TeamInfo[]>(CACHE_KEY);
  if (cached) _data = cached;
}

function _fetchFresh() {
  if (_inflightPromise) return;
  _inflightPromise = fetchTeams()
    .then((d) => {
      _data = d;
      setCached(CACHE_KEY, d);
      _inflightPromise = null;
      _notify();
      return d;
    })
    .catch((e) => {
      _inflightPromise = null;
      _notify();
      throw e;
    });
}

export function useTeams() {
  _hydrateFromStorage();

  const [, rerender] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => rerender((n) => n + 1);
    _listeners.add(refresh);

    if (!_data || isStale(CACHE_KEY)) {
      try {
        _fetchFresh();
      } catch (e: unknown) {
        if (!_data) setError(e instanceof Error ? e.message : "Failed to load teams");
      }
    }

    return () => { _listeners.delete(refresh); };
  }, []);

  return { teams: _data ?? [], loading: !_data && !error, error };
}
