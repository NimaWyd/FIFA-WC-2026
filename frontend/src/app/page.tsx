"use client";
import { useState } from "react";
import { TrophyIcon, ArrowsRightLeftIcon } from "@heroicons/react/24/solid";
import { useTeams } from "@/hooks/useTeams";
import { usePredict } from "@/hooks/usePredict";
import TeamCombobox from "@/components/TeamCombobox";
import StageSelect from "@/components/StageSelect";
import PredictButton from "@/components/PredictButton";
import ProbabilityBars from "@/components/ProbabilityBars";
import ScorelineGrid from "@/components/ScorelineGrid";
import ExpectedGoals from "@/components/ExpectedGoals";
import ExplanationPanel from "@/components/ExplanationPanel";
import MetadataBadge from "@/components/MetadataBadge";
import type { TeamInfo } from "@/lib/types";

export default function Home() {
  const { teams, loading: teamsLoading } = useTeams();
  const { predict, result, loading: predLoading, error, reset } = usePredict();

  const [homeTeam, setHomeTeam] = useState<TeamInfo | null>(null);
  const [awayTeam, setAwayTeam] = useState<TeamInfo | null>(null);
  const [matchDate, setMatchDate] = useState("2026-06-14");
  const [stage, setStage] = useState("Group Stage");

  function swap() {
    setHomeTeam(awayTeam);
    setAwayTeam(homeTeam);
    reset();
  }

  function handlePredict() {
    if (!homeTeam || !awayTeam) return;
    predict({
      home_team: homeTeam.canonical_name,
      away_team: awayTeam.canonical_name,
      match_date: matchDate,
      competition: "FIFA World Cup",
      neutral: true,
      tournament_stage: stage,
    });
  }

  return (
    <main className="min-h-screen bg-[#0a0e1a]">
      {/* Header */}
      <div className="border-b border-slate-800 bg-[#0d1428]">
        <div className="max-w-3xl mx-auto px-4 py-6 flex items-center gap-3">
          <TrophyIcon className="h-8 w-8 text-[#d4af37]" />
          <div>
            <h1 className="text-xl font-bold text-white">FIFA WC 2026 Predictor</h1>
            <p className="text-sm text-slate-400">AI-powered match outcome predictions</p>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8 flex flex-col gap-6">
        {/* Match Form */}
        <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6 flex flex-col gap-5">
          <h2 className="font-bold text-slate-200 text-lg">Select Match</h2>

          {teamsLoading ? (
            <div className="text-slate-400 text-sm py-4 text-center">Loading teams…</div>
          ) : (
            <div className="relative flex flex-col gap-4">
              {/* Team selectors */}
              <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-end">
                <TeamCombobox
                  label="Home Team"
                  value={homeTeam}
                  onChange={(t) => { setHomeTeam(t); reset(); }}
                  teams={teams}
                  disabledTeam={awayTeam}
                  placeholder="Search home team…"
                />
                <button
                  onClick={swap}
                  className="mb-0.5 p-2.5 rounded-lg bg-[#111d3c] border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
                  title="Swap teams"
                >
                  <ArrowsRightLeftIcon className="h-5 w-5" />
                </button>
                <TeamCombobox
                  label="Away Team"
                  value={awayTeam}
                  onChange={(t) => { setAwayTeam(t); reset(); }}
                  teams={teams}
                  disabledTeam={homeTeam}
                  placeholder="Search away team…"
                />
              </div>

              {/* Date + Stage */}
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Match Date</label>
                  <input
                    type="date"
                    value={matchDate}
                    onChange={(e) => { setMatchDate(e.target.value); reset(); }}
                    className="rounded-lg bg-[#111d3c] border border-slate-600 text-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#d4af37]"
                  />
                </div>
                <StageSelect value={stage} onChange={(s) => { setStage(s); reset(); }} />
              </div>

              <PredictButton
                loading={predLoading}
                disabled={!homeTeam || !awayTeam}
                onClick={handlePredict}
              />
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
            {error === "Failed to fetch"
              ? "Cannot connect to backend — make sure the FastAPI server is running on port 8000."
              : error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div id="results" className="flex flex-col gap-4">
            {/* Match header */}
            <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
              <div className="flex items-center justify-between text-slate-400 text-sm mb-4">
                <span>{result.match_date}</span>
                <span className="bg-[#111d3c] border border-slate-700 px-2 py-0.5 rounded-full text-xs">{stage}</span>
              </div>
              <div className="flex items-center justify-between gap-4 text-center">
                <div className="flex-1">
                  <div className="text-2xl font-bold text-white">{result.home_team}</div>
                  <div className="text-sm text-slate-400 mt-1">Home</div>
                </div>
                <div className="text-slate-500 font-bold text-xl">vs</div>
                <div className="flex-1">
                  <div className="text-2xl font-bold text-white">{result.away_team}</div>
                  <div className="text-sm text-slate-400 mt-1">Away</div>
                </div>
              </div>
            </div>

            {/* Probability bars */}
            <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
              <ProbabilityBars
                probabilities={result.probabilities}
                homeTeam={result.home_team}
                awayTeam={result.away_team}
              />
            </div>

            {/* Scorelines */}
            {result.top_scorelines.length > 0 && (
              <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
                <ScorelineGrid scorelines={result.top_scorelines} />
              </div>
            )}

            {/* xG */}
            {(result.expected_goals.home > 0 || result.expected_goals.away > 0) && (
              <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
                <ExpectedGoals
                  xg={result.expected_goals}
                  homeTeam={result.home_team}
                  awayTeam={result.away_team}
                />
              </div>
            )}

            {/* Explanation */}
            <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
              <ExplanationPanel
                explanation={result.explanation}
                homeTeam={result.home_team}
                awayTeam={result.away_team}
              />
            </div>

            {/* Metadata */}
            <MetadataBadge result={result} />
          </div>
        )}
      </div>
    </main>
  );
}
