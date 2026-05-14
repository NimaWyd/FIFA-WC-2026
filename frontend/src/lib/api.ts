import type { TeamInfo, PredictRequest, PredictResponse, ModelInfo, SimulationResponse, BracketResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

if (
  typeof window !== "undefined" &&
  !process.env.NEXT_PUBLIC_API_BASE_URL &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1"
) {
  console.warn(
    "[FIFA Predictor] NEXT_PUBLIC_API_BASE_URL is not set. " +
    "API calls will target http://127.0.0.1:8000 which will fail in production. " +
    "Set this variable in your deployment environment."
  );
}

const DEFAULT_TIMEOUT_MS = 12_000;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Request timed out — the backend took too long to respond.");
    }
    throw e;
  } finally {
    clearTimeout(id);
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const confOrder: Record<string, number> = {
  UEFA: 0, CONMEBOL: 1, CONCACAF: 2, CAF: 3, AFC: 4, OFC: 5, UNKNOWN: 6,
};

let teamsCache: TeamInfo[] | null = null;

export async function fetchTeams(): Promise<TeamInfo[]> {
  if (teamsCache) return teamsCache;
  const res = await fetchWithTimeout(`${BASE}/teams`);
  const teams = await handleResponse<TeamInfo[]>(res);
  teams.sort((a, b) => {
    const ca = confOrder[a.confederation] ?? 6;
    const cb = confOrder[b.confederation] ?? 6;
    if (ca !== cb) return ca - cb;
    if (a.fifa_rank == null && b.fifa_rank == null) return 0;
    if (a.fifa_rank == null) return 1;
    if (b.fifa_rank == null) return -1;
    return a.fifa_rank - b.fifa_rank;
  });
  teamsCache = teams;
  return teams;
}

export async function predict(req: PredictRequest): Promise<PredictResponse> {
  const res = await fetchWithTimeout(`${BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return handleResponse<PredictResponse>(res);
}

export async function fetchModelInfo(): Promise<ModelInfo> {
  const res = await fetchWithTimeout(`${BASE}/model-info`);
  return handleResponse<ModelInfo>(res);
}

export async function fetchTeam(name: string): Promise<TeamInfo> {
  const res = await fetchWithTimeout(`${BASE}/teams/${encodeURIComponent(name)}`);
  return handleResponse<TeamInfo>(res);
}

export async function fetchSimulation(): Promise<SimulationResponse> {
  const res = await fetchWithTimeout(`${BASE}/simulate`, {}, 90_000);
  return handleResponse<SimulationResponse>(res);
}

export async function fetchBracket(): Promise<BracketResponse> {
  const res = await fetchWithTimeout(`${BASE}/bracket`, {}, 90_000);
  return handleResponse<BracketResponse>(res);
}
