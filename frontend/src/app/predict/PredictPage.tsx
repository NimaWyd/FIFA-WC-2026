"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowsRightLeftIcon, SparklesIcon } from "@heroicons/react/24/solid";
import { useTeams } from "@/hooks/useTeams";
import { usePredict } from "@/hooks/usePredict";
import TeamCombobox from "@/components/TeamCombobox";
import StageSelect from "@/components/StageSelect";
import PredictButton from "@/components/PredictButton";
import ProbabilityBars from "@/components/ProbabilityBars";
import WinnerCallout from "@/components/WinnerCallout";
import ScorelineGrid from "@/components/ScorelineGrid";
import ExpectedGoals from "@/components/ExpectedGoals";
import ExplanationPanel from "@/components/ExplanationPanel";
import MetadataBadge from "@/components/MetadataBadge";
import MatchScoreboard from "@/components/MatchScoreboard";
import FlagIcon from "@/components/FlagIcon";
import { WC2026_TEAMS } from "@/lib/wc2026Teams";
import { WC2026_GROUPS } from "@/lib/wc2026Groups";
import type { TeamInfo } from "@/lib/types";
import { selectScoreline } from "@/lib/scoreline";

const TOURNAMENT_START = "2026-06-11";
const TOURNAMENT_END = "2026-07-19";
const MIN_WC_FILTER_TEAMS = 10;

const ALL_GROUP_MATCHES = WC2026_GROUPS.flatMap((g) => g.matches);

export default function PredictPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { teams: allTeams, loading: teamsLoading, error: teamsError } = useTeams();
  const { predict, result, loading: predLoading, error, reset } = usePredict();

  const [homeTeam, setHomeTeam] = useState<TeamInfo | null>(null);
  const [awayTeam, setAwayTeam] = useState<TeamInfo | null>(null);
  const [matchDate, setMatchDate] = useState(TOURNAMENT_START);
  const [stage, setStage] = useState("Group Stage");
  const [showAllTeams, setShowAllTeams] = useState(false);
  const [dateError, setDateError] = useState<string | null>(null);
  const [paramsApplied, setParamsApplied] = useState(false);

  const resultsRef = useRef<HTMLDivElement>(null);

  // Pre-fill from query params once teams are loaded
  useEffect(() => {
    if (paramsApplied || teamsLoading) return;

    const homeParam = searchParams.get("home");
    const awayParam = searchParams.get("away");
    const dateParam = searchParams.get("date");
    const stageParam = searchParams.get("stage");

    if (homeParam) {
      const found = allTeams.find((t) => t.canonical_name === homeParam);
      if (found) setHomeTeam(found);
    }
    if (awayParam) {
      const found = allTeams.find((t) => t.canonical_name === awayParam);
      if (found) setAwayTeam(found);
    }
    if (dateParam && dateParam >= TOURNAMENT_START && dateParam <= TOURNAMENT_END) {
      setMatchDate(dateParam);
    }
    if (stageParam) setStage(stageParam);

    setParamsApplied(true);
  }, [teamsLoading, allTeams, searchParams, paramsApplied]); // allTeams needed for team name lookup

  // Keep URL in sync with current form state
  useEffect(() => {
    if (!paramsApplied) return;
    const params = new URLSearchParams();
    if (homeTeam) params.set("home", homeTeam.canonical_name);
    if (awayTeam) params.set("away", awayTeam.canonical_name);
    params.set("date", matchDate);
    params.set("stage", stage);
    router.replace(`/predict?${params.toString()}`, { scroll: false });
  }, [homeTeam, awayTeam, matchDate, stage, paramsApplied, router]);

  useEffect(() => {
    if (result) {
      resultsRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [result]);

  const teams = useMemo(() => {
    if (showAllTeams) return allTeams;
    const filtered = allTeams.filter((t) => WC2026_TEAMS.has(t.canonical_name));
    return filtered.length >= MIN_WC_FILTER_TEAMS ? filtered : allTeams;
  }, [allTeams, showAllTeams]);

  function swap() {
    setHomeTeam(awayTeam);
    setAwayTeam(homeTeam);
    reset();
  }

  function handlePredict() {
    if (!homeTeam || !awayTeam) return;
    if (matchDate < TOURNAMENT_START || matchDate > TOURNAMENT_END) {
      setDateError(`Date must be between ${TOURNAMENT_START} and ${TOURNAMENT_END}.`);
      return;
    }
    setDateError(null);
    predict({
      home_team: homeTeam.canonical_name,
      away_team: awayTeam.canonical_name,
      match_date: matchDate,
      competition: "FIFA World Cup",
      neutral: true,
      tournament_stage: stage,
    });
  }

  function handleRandomFixture() {
    const match = ALL_GROUP_MATCHES[Math.floor(Math.random() * ALL_GROUP_MATCHES.length)];
    const home = allTeams.find((t) => t.canonical_name === match.home);
    const away = allTeams.find((t) => t.canonical_name === match.away);
    if (home) setHomeTeam(home);
    if (away) setAwayTeam(away);
    setMatchDate(match.date);
    setStage("Group Stage");
    setDateError(null);
    reset();
  }

  return (
    <main className="min-h-screen bg-navy-900">
      <div className="max-w-4xl mx-auto px-4 py-10 flex flex-col gap-6">
        {/* Page header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Predict a Match</h1>
            <p className="text-slate-400 text-sm mt-1">
              Pick any two teams and get an AI-powered outcome prediction.
            </p>
          </div>
          <button
            onClick={handleRandomFixture}
            disabled={teamsLoading || predLoading || allTeams.length === 0}
            className="flex-shrink-0 flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-navy-600 text-slate-400 hover:text-white hover:border-slate-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <SparklesIcon className="h-3.5 w-3.5" />
            Try a random fixture
          </button>
        </div>

        {/* Selector card */}
        <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-5">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-200 text-lg">Select Match</h2>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">
                {showAllTeams ? "All teams" : "WC 2026 only"} · {teams.length} available
              </span>
              <button
                onClick={() => {
                  setShowAllTeams((v) => !v);
                  setHomeTeam(null);
                  setAwayTeam(null);
                  reset();
                }}
                className="text-xs px-2 py-1 rounded border border-navy-600 text-slate-500 hover:text-white hover:border-slate-500 transition-colors"
              >
                {showAllTeams ? "Filter WC26" : "Show all"}
              </button>
            </div>
          </div>

          {teamsError && (
            <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
              Failed to load teams: {teamsError}
            </div>
          )}

          {teamsLoading ? (
            <div className="text-slate-400 text-sm py-4 text-center">Loading teams…</div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-end overflow-visible">
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
                  disabled={!homeTeam && !awayTeam}
                  className="mb-0.5 p-2.5 rounded-lg bg-navy-700 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-slate-400 disabled:hover:border-navy-600"
                  title="Swap teams"
                  aria-label="Swap home and away teams"
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

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1">
                  <label
                    htmlFor="match-date"
                    className="text-sm font-semibold text-slate-300 uppercase tracking-wider"
                  >
                    Match Date
                  </label>
                  <input
                    id="match-date"
                    type="date"
                    value={matchDate}
                    min={TOURNAMENT_START}
                    max={TOURNAMENT_END}
                    onChange={(e) => {
                      setMatchDate(e.target.value);
                      setDateError(null);
                      reset();
                    }}
                    className="rounded-lg bg-navy-700 border border-navy-600 text-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-fifa-blue [color-scheme:dark]"
                  />
                  {dateError && <p className="text-red-400 text-xs mt-1">{dateError}</p>}
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

        {error && (
          <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
            {error === "Failed to fetch"
              ? "Cannot connect to backend — make sure the FastAPI server is running on port 8000."
              : error}
          </div>
        )}

        {result && (
          <div ref={resultsRef} className="flex flex-col gap-4">
            <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6">
              <div className="flex items-center justify-between text-slate-400 text-sm mb-4">
                <span>{result.match_date}</span>
                <span className="bg-navy-700 border border-navy-600 px-2 py-0.5 rounded-full text-xs">
                  {stage} · FIFA World Cup 2026
                </span>
              </div>
              <div className="flex items-center justify-between gap-4 text-center">
                <div className="flex-1">
                  <FlagIcon team={result.home_team} className="w-16 h-12 rounded mb-3 inline-block" />
                  <div className="text-xl font-bold text-white">{result.home_team}</div>
                  <div className="text-sm text-slate-400 mt-1">Home</div>
                </div>
                <div className="text-slate-500 font-bold text-2xl">vs</div>
                <div className="flex-1">
                  <FlagIcon team={result.away_team} className="w-16 h-12 rounded mb-3 inline-block" />
                  <div className="text-xl font-bold text-white">{result.away_team}</div>
                  <div className="text-sm text-slate-400 mt-1">Away</div>
                </div>
              </div>
            </div>

            {result.top_scorelines.length > 0 &&
              (() => {
                const p = result.probabilities;
                const dominant =
                  p.home_win > p.draw && p.home_win > p.away_win
                    ? "H"
                    : p.away_win > p.draw && p.away_win > p.home_win
                    ? "A"
                    : "D";
                const [hg, ag] = selectScoreline(
                  dominant,
                  result.top_scorelines,
                  result.expected_goals?.home ?? 1,
                  result.expected_goals?.away ?? 1,
                );
                return (
                  <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6">
                    <MatchScoreboard
                      homeTeam={result.home_team}
                      awayTeam={result.away_team}
                      homeGoals={hg}
                      awayGoals={ag}
                    />
                  </div>
                );
              })()}

            <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6">
              <WinnerCallout
                probabilities={result.probabilities}
                homeTeam={result.home_team}
                awayTeam={result.away_team}
              />
              <ProbabilityBars
                probabilities={result.probabilities}
                homeTeam={result.home_team}
                awayTeam={result.away_team}
                confidence={result.confidence}
              />
            </div>

            {result.top_scorelines.length > 0 && (
              <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6">
                <ScorelineGrid scorelines={result.top_scorelines} />
              </div>
            )}

            {result.expected_goals &&
              (result.expected_goals.home > 0 || result.expected_goals.away > 0) && (
                <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6">
                  <ExpectedGoals
                    xg={result.expected_goals}
                    homeTeam={result.home_team}
                    awayTeam={result.away_team}
                  />
                </div>
              )}

            <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6">
              <ExplanationPanel
                explanation={result.explanation}
                homeTeam={result.home_team}
                awayTeam={result.away_team}
              />
            </div>

            <MetadataBadge result={result} />
          </div>
        )}
      </div>
    </main>
  );
}
