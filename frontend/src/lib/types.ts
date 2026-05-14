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

export interface PredictResponse {
  home_team: string;
  away_team: string;
  match_date: string;
  probabilities: Probabilities;
  top_scorelines: Scoreline[];
  expected_goals: { home: number; away: number };
  explanation: Explanation;
  metadata: Record<string, unknown>;
  confidence?: ConfidenceInterval;
}

export interface PredictRequest {
  home_team: string;
  away_team: string;
  match_date: string;
  competition?: string;
  neutral?: boolean;
  tournament_stage?: string;
}

export interface ModelInfo {
  model_version: string;
  model_type: string;
  training_cutoff: string;
  feature_set_version: string;
  enabled_features: string[];
  scoreline_model_status: string;
  config_summary: Record<string, unknown>;
}

export interface TeamSimResult {
  team: string;
  group: string;
  group_exit: number;
  round_of_32: number;
  quarter_final: number;
  semi_final: number;
  final: number;
  champion: number;
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
