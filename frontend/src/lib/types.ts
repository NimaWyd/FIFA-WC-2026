export interface TeamInfo {
  canonical_name: string;
  display_name: string;
  confederation: "UEFA" | "AFC" | "CAF" | "CONCACAF" | "CONMEBOL" | "OFC" | "UNKNOWN";
  fifa_rank: number | null;
  aliases: string[];
  is_known: boolean;
  default_metadata: Record<string, unknown>;
}

export interface Probabilities {
  home_win: number;
  draw: number;
  away_win: number;
}

export interface Scoreline {
  scoreline: string;
  probability: number;
}

export interface Explanation {
  elo_diff: number;
  home_elo: number;
  away_elo: number;
  form_diff: number;
  home_form: number;
  away_form: number;
  rank_diff: number;
  home_rank: number;
  away_rank: number;
  elo_win_prob: number;
  competition_weight: number;
  is_same_confederation: boolean;
  data_note: string;
}

export interface ConfidenceInterval {
  home_win: [number, number];
  draw: [number, number];
  away_win: [number, number];
}

export interface VenueInfo {
  name: string;
  city: string;
  country: string;
  capacity: number;
  altitude_m: number;
  surface: string;
  is_dome: boolean;
  image_url?: string | null;
  wikipedia_url?: string | null;
}

export interface PredictResponse {
  home_team: string;
  away_team: string;
  match_date: string;
  probabilities: Probabilities;
  top_scorelines: Scoreline[];
  expected_goals?: { home: number; away: number };
  explanation: Explanation;
  metadata: Record<string, unknown>;
  confidence?: ConfidenceInterval;
  venue?: VenueInfo | null;
}

export interface PredictRequest {
  home_team: string;
  away_team: string;
  match_date: string;
  competition?: string;
  neutral?: boolean;
  tournament_stage?: string;
}

export interface AccuracyMetrics {
  accuracy: number;
  brier_score: number;
  log_loss: number;
  test_rows: number;
}

export interface ModelInfo {
  model_version: string;
  model_type: string;
  training_cutoff: string;
  feature_set_version: string;
  enabled_features: string[];
  scoreline_model_status: string;
  config_summary: Record<string, unknown>;
  accuracy_metrics: AccuracyMetrics | null;
}

export interface TeamSimResult {
  team: string;
  group: string;
  group_exit: number;
  round_of_32: number;
  round_of_16: number;
  quarter_final: number;
  semi_final: number;
  third_place: number;
  final: number;
  champion: number;
}

/** P(team reaches at least this stage) — use these for all display purposes */
export function reachProb(t: TeamSimResult, stage: "r32" | "r16" | "qf" | "sf" | "final" | "champion"): number {
  switch (stage) {
    case "r32":     return 1 - t.group_exit;
    case "r16":     return 1 - t.group_exit - (t.round_of_32 ?? 0);
    case "qf":      return 1 - t.group_exit - (t.round_of_32 ?? 0) - (t.round_of_16 ?? 0);
    case "sf":      return (t.semi_final ?? 0) + (t.third_place ?? 0) + t.final + t.champion;
    case "final":   return t.final + t.champion;
    case "champion":return t.champion;
  }
}

export interface SimulationResponse {
  n_simulations: number;
  teams: TeamSimResult[];
  generated_at: string;
}

export interface BracketMatch {
  match_id: string;
  round: string;
  team1: string;
  team2: string;
  team1_win_prob: number;
  team2_win_prob: number;
  predicted_winner: string;
}

export interface BracketRound {
  round: string;
  matches: BracketMatch[];
}

export interface BracketResponse {
  rounds: BracketRound[];
  group_standings: Record<string, string[]>;
  champion: string;
  generated_at: string;
}

export interface LiveMatch {
  id: string;
  utc_date: string;
  local_date: string;
  status: "SCHEDULED" | "TIMED" | "IN_PLAY" | "PAUSED" | "FINISHED" | "POSTPONED" | "SUSPENDED" | "CANCELLED" | "AWARDED";
  minute?: number | null;
  stage: string;
  group?: string | null;
  matchday?: number | null;
  home_team: string;
  away_team: string;
  home_score?: number | null;
  away_score?: number | null;
  halftime_home?: number | null;
  halftime_away?: number | null;
  venue?: string | null;
}

export interface LiveMatchesResponse {
  matches: LiveMatch[];
  source: string;
  fetched_at: string;
  has_live: boolean;
}
