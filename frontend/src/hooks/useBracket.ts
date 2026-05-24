"use client";
import { useEffect, useState } from "react";
import { fetchBracket } from "@/lib/api";
import type { BracketResponse } from "@/lib/types";
import { getCached, setCached, isStale } from "@/lib/localCache";

const CACHE_KEY = "bracket_v1";

let _data: BracketResponse | null = null;
let _inflightPromise: Promise<BracketResponse> | null = null;
const _listeners: Set<() => void> = new Set();

function _notify() {
  _listeners.forEach((fn) => fn());
}

function _hydrateFromStorage() {
  if (_data) return;
  const cached = getCached<BracketResponse>(CACHE_KEY);
  if (cached) _data = cached;
}

function _fetchFresh() {
  if (_inflightPromise) return;
  _inflightPromise = fetchBracket()
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

export function useBracket() {
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
        if (!_data) setError(e instanceof Error ? e.message : "Failed to load bracket");
      }
    }

    return () => { _listeners.delete(refresh); };
  }, []);

  return { data: _data, loading: !_data && !error, error };
}
