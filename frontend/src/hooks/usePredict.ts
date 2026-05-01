"use client";
import { useCallback, useState } from "react";
import { predict as apiPredict } from "@/lib/api";
import type { PredictRequest, PredictResponse } from "@/lib/types";

export function usePredict() {
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runPredict = useCallback(async (req: PredictRequest) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPredict(req);
      setResult(res);
      setTimeout(() => {
        document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { predict: runPredict, result, loading, error, reset };
}
