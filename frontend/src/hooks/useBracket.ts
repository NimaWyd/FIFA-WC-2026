"use client";
import { useEffect, useState } from "react";
import { fetchBracket } from "@/lib/api";
import type { BracketResponse } from "@/lib/types";

export function useBracket() {
  const [data, setData] = useState<BracketResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchBracket()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
