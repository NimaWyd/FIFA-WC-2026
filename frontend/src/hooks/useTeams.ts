"use client";
import { useEffect, useState } from "react";
import { fetchTeams } from "@/lib/api";
import type { TeamInfo } from "@/lib/types";

export function useTeams() {
  const [teams, setTeams] = useState<TeamInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTeams()
      .then(setTeams)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { teams, loading, error };
}
