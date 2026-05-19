"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { fetchLiveMatches } from "@/lib/api";
import type { LiveMatchesResponse } from "@/lib/types";

const POLL_INTERVAL_MS = 60_000;

export function useLiveMatches() {
  const [data, setData] = useState<LiveMatchesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const load = useCallback(async () => {
    try {
      const d = await fetchLiveMatches();
      setData(d);
      setError(null);
      setLastRefresh(new Date());
      if (d.has_live) {
        timerRef.current = setTimeout(load, POLL_INTERVAL_MS);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load matches";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [load]);

  return { data, loading, error, lastRefresh, refresh: load };
}
