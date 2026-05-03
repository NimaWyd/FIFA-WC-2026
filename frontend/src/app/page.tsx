"use client";
import { useEffect, useMemo, useRef, useState } from "react";
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
import GroupBracket from "@/components/GroupBracket";
import GroupView from "@/components/GroupView";
import { WC2026_TEAMS } from "@/lib/wc2026Teams";
import { WCGroup, WCMatch } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";
import type { TeamInfo } from "@/lib/types";

const TOURNAMENT_START = "2026-06-11";
const TOURNAMENT_END = "2026-07-19";
const MIN_WC_FILTER_TEAMS = 10;

type Tab = "bracket" | "predictor";

export default function Home() {
  const { teams: allTeams, loading: teamsLoading, error: teamsError } = useTeams();
  const { predict, result, loading: predLoading, error, reset } = usePredict();

  const [tab, setTab] = useState<Tab>("bracket");
  const [selectedGroup, setSelectedGroup] = useState<WCGroup | null>(null);

  const [homeTeam, setHomeTeam] = useState<TeamInfo | null>(null);
  const [awayTeam, setAwayTeam] = useState<TeamInfo | null>(null);
  const [matchDate, setMatchDate] = useState(TOURNAMENT_START);
  const [stage, setStage] = useState("Group Stage");
  const [showAllTeams, setShowAllTeams] = useState(false);
  const [dateError, setDateError] = useState<string | null>(null);

  const resultsRef = useRef<HTMLDivElement>(null);

  // Scroll to results when a new prediction arrives
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

  function handleMatchPredict(match: WCMatch) {
    const home = allTeams.find((t) => t.canonical_name === match.home);
    const away = allTeams.find((t) => t.canonical_name === match.away);
    if (home) setHomeTeam(home);
    if (away) setAwayTeam(away);
    setMatchDate(match.date);
    setStage("Group Stage");
    setDateError(null);
    reset();
    setTab("predictor");
  }

  function handleSelectGroup(group: WCGroup) {
    setSelectedGroup(group);
  }

  function handleBackToBracket() {
    setSelectedGroup(null);
  }

  return (
    <main className="min-h-screen bg-[#0a0e1a]">
      {/* Header */}
      <div className="border-b border-slate-800 bg-[#0d1428]">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <TrophyIcon className="h-7 w-7 text-[#d4af37] flex-shrink-0" />
          <div>
            <h1 className="text-lg font-bold text-white leading-tight">FIFA WC 2026 Predictor</h1>
            <p className="text-xs text-slate-400">AI-powered match outcome predictions</p>
          </div>
        </div>

        {/* Tab bar */}
        <div className="max-w-4xl mx-auto px-4 flex items-center gap-0 border-t border-slate-800/50">
          <button
            onClick={() => setTab("bracket")}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
              tab === "bracket"
                ? "border-[#d4af37] text-[#d4af37]"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Group Stage
          </button>
          <button
            onClick={() => setTab("predictor")}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
              tab === "predictor"
                ? "border-[#d4af37] text-[#d4af37]"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Predict Match
          </button>
          {tab === "predictor" && (
            <div className="ml-auto flex items-center gap-2 py-2">
              <span className="text-xs text-slate-500">
                {showAllTeams ? "All teams" : "WC 2026 only"}
              </span>
              <button
                onClick={() => {
                  setShowAllTeams((v) => !v);
                  setHomeTeam(null);
                  setAwayTeam(null);
                  reset();
                }}
                className="text-xs px-2 py-1 rounded border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
              >
                {showAllTeams ? "Filter WC26" : "Show all"}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col gap-6">
        {/* ── Group Stage tab ── */}
        {tab === "bracket" && (
          selectedGroup ? (
            <GroupView
              group={selectedGroup}
              onBack={handleBackToBracket}
              onPredict={handleMatchPredict}
            />
          ) : (
            <GroupBracket onSelectGroup={handleSelectGroup} />
          )
        )}

        {/* ── Predict Match tab ── */}
        {tab === "predictor" && (
          <>
            <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6 flex flex-col gap-5">
              <div className="flex items-center justify-between">
                <h2 className="font-bold text-slate-200 text-lg">Select Match</h2>
                <span className="text-xs text-slate-500">{teams.length} teams available</span>
              </div>

              {/* Teams API error */}
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
                      className="mb-0.5 p-2.5 rounded-lg bg-[#111d3c] border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
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
                      <label htmlFor="match-date" className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
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
                        className="rounded-lg bg-[#111d3c] border border-slate-600 text-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#d4af37] [color-scheme:dark]"
                      />
                      {dateError && (
                        <p className="text-red-400 text-xs mt-1">{dateError}</p>
                      )}
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

            {/* Prediction error */}
            {error && (
              <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
                {error === "Failed to fetch"
                  ? "Cannot connect to backend — make sure the FastAPI server is running on port 8000."
                  : error}
              </div>
            )}

            {/* Results */}
            {result && (
              <div ref={resultsRef} className="flex flex-col gap-4">
                <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
                  <div className="flex items-center justify-between text-slate-400 text-sm mb-4">
                    <span>{result.match_date}</span>
                    <span className="bg-[#111d3c] border border-slate-700 px-2 py-0.5 rounded-full text-xs">
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

                <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
                  <ProbabilityBars
                    probabilities={result.probabilities}
                    homeTeam={result.home_team}
                    awayTeam={result.away_team}
                  />
                </div>

                {result.top_scorelines.length > 0 && (
                  <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
                    <ScorelineGrid scorelines={result.top_scorelines} />
                  </div>
                )}

                {result.expected_goals &&
                  (result.expected_goals.home > 0 || result.expected_goals.away > 0) && (
                    <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
                      <ExpectedGoals
                        xg={result.expected_goals}
                        homeTeam={result.home_team}
                        awayTeam={result.away_team}
                      />
                    </div>
                  )}

                <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
                  <ExplanationPanel
                    explanation={result.explanation}
                    homeTeam={result.home_team}
                    awayTeam={result.away_team}
                  />
                </div>

                <MetadataBadge result={result} />
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
