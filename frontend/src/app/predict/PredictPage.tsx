"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
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
import FlagIcon from "@/components/FlagIcon";
import StadiumCard from "@/components/StadiumCard";
import { WC2026_TEAMS } from "@/lib/wc2026Teams";
import { WC2026_GROUPS } from "@/lib/wc2026Groups";
import type { TeamInfo } from "@/lib/types";
import { selectScoreline } from "@/lib/scoreline";

const TOURNAMENT_START = "2026-06-11";
const TOURNAMENT_END = "2026-07-19";

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] as const },
  }),
};

const MIN_WC_FILTER_TEAMS = 10;
const ALL_GROUP_MATCHES = WC2026_GROUPS.flatMap((g) => g.matches);

function formatMatchDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

function TeamPanel({
  team,
  side,
}: {
  team: TeamInfo | null;
  side: "home" | "away";
}) {
  const isHome = side === "home";
  const label = isHome ? "Home" : "Away";
  const labelColor = isHome ? "text-fifa-blue" : "text-gold-500";
  const emptyLabel = isHome ? "HOME" : "AWAY";

  return (
    <div className="flex flex-col items-center gap-3 py-4">
      {team ? (
        <>
          <motion.div
            key={team.canonical_name}
            initial={{ scale: 0.82, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            whileHover={{ scale: 1.06 }}
            transition={{ type: "spring", stiffness: 320, damping: 22 }}
            className="relative cursor-default"
          >
            {/* outer halo */}
            <div
              className={`absolute -inset-5 rounded-3xl blur-2xl opacity-50 ${isHome ? "bg-fifa-blue" : "bg-gold-500"}`}
            />
            {/* inner edge glow */}
            <div
              className={`absolute -inset-1 rounded-2xl blur-md opacity-30 ${isHome ? "bg-fifa-blue" : "bg-gold-500"}`}
            />
            <FlagIcon
              team={team.canonical_name}
              className="relative w-24 h-[64px] sm:w-40 sm:h-[107px] rounded-xl shadow-2xl"
            />
          </motion.div>
          <div className="text-center mt-1">
            <div className={`text-[10px] font-bold tracking-[0.25em] uppercase ${labelColor}`}>{label}</div>
            <div className="font-anton text-xl text-white mt-0.5 leading-none">
              {team.canonical_name === "United States" ? "USA" : team.canonical_name}
            </div>
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <div className="w-24 h-[64px] sm:w-40 sm:h-[107px] rounded-xl border-2 border-dashed border-navy-600 flex items-center justify-center">
            <span className="text-navy-600 text-[10px] font-bold tracking-wider">{emptyLabel}</span>
          </div>
          <div className={`text-[10px] font-bold tracking-[0.25em] uppercase ${labelColor} opacity-40`}>
            {label}
          </div>
        </div>
      )}
    </div>
  );
}

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
  const [venueCity, setVenueCity] = useState<string | null>(null);

  const resultsRef = useRef<HTMLDivElement>(null);

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
  }, [teamsLoading, allTeams, searchParams, paramsApplied]);

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

  useEffect(() => {
    const match = ALL_GROUP_MATCHES.find(
      (m) =>
        m.home === homeTeam?.canonical_name &&
        m.away === awayTeam?.canonical_name &&
        m.date === matchDate,
    );
    setVenueCity(match?.venue ?? null);
  }, [homeTeam, awayTeam, matchDate]);

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
    <main className="min-h-screen bg-navy-900 overflow-x-hidden">
      {/* ── Hero ──────────────────────────────────────────────── */}
      <div className="relative overflow-hidden">
        <div className="pointer-events-none select-none absolute inset-0">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full border border-white/[0.025]" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full border border-white/[0.025]" />
        </div>
        <div className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-28 bg-fifa-blue/15 blur-[70px] rounded-full" />

        <div className="relative max-w-4xl mx-auto px-4 pt-14 pb-10 flex flex-col items-center text-center gap-3">
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-[11px] font-bold tracking-[0.35em] text-fifa-blue uppercase"
          >
            FIFA World Cup 2026 · AI Predictor
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.55, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="font-anton text-[64px] sm:text-[90px] leading-none tracking-wide text-white uppercase"
          >
            Match Predictor
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="text-slate-500 text-sm max-w-sm"
          >
            Pick any two teams and let the AI predict the outcome.
          </motion.p>
        </div>
      </div>

      {/* ── Form ──────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 pb-16 flex flex-col gap-5">
        {/* Top controls */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-600">
              {showAllTeams ? "All teams" : "WC 2026 only"} · {teams.length} available
            </span>
            <button
              onClick={() => {
                setShowAllTeams((v) => !v);
                setHomeTeam(null);
                setAwayTeam(null);
                reset();
              }}
              className="text-xs px-2.5 py-1 rounded-lg border border-navy-600 text-slate-500 hover:text-white hover:border-slate-500 transition-colors"
            >
              {showAllTeams ? "Filter WC26" : "Show all"}
            </button>
          </div>
          <button
            onClick={handleRandomFixture}
            disabled={teamsLoading || predLoading || allTeams.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue/50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <SparklesIcon className="h-3.5 w-3.5" />
            Random fixture
          </button>
        </div>

        {/* Stadium poster form */}
        <div className="relative overflow-visible rounded-2xl border border-navy-600 bg-navy-800">
          {/* Shimmer top edge */}
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-fifa-blue/50 to-transparent rounded-t-2xl" />

          {/* Split background tints */}
          <div className="absolute inset-0 pointer-events-none rounded-2xl overflow-hidden">
            <div className="absolute inset-y-0 left-0 w-1/2 bg-gradient-to-r from-fifa-blue/[0.07] to-transparent" />
            <div className="absolute inset-y-0 right-0 w-1/2 bg-gradient-to-l from-gold-500/[0.07] to-transparent" />
          </div>

          <div className="relative z-10 p-6 flex flex-col gap-5">
            {teamsError && (
              <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
                Failed to load teams: {teamsError}
              </div>
            )}

            {teamsLoading ? (
              <div className="text-slate-400 text-sm py-8 text-center">Loading teams…</div>
            ) : (
              <>
                {/* Team panels + comboboxes */}
                <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-center">
                  {/* Home */}
                  <div className="flex flex-col gap-3">
                    <TeamPanel team={homeTeam} side="home" />
                    <TeamCombobox
                      label="Home Team"
                      value={homeTeam}
                      onChange={(t) => { setHomeTeam(t); reset(); }}
                      teams={teams}
                      disabledTeam={awayTeam}
                      placeholder="Search home team…"
                    />
                  </div>

                  {/* Center: VS + swap */}
                  <div className="flex flex-col items-center gap-3 pt-4">
                    <span className="font-anton text-3xl text-navy-600 tracking-widest">VS</span>
                    <button
                      onClick={swap}
                      disabled={!homeTeam && !awayTeam}
                      className="p-2.5 rounded-lg bg-navy-900/60 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Swap teams"
                      aria-label="Swap home and away teams"
                    >
                      <ArrowsRightLeftIcon className="h-5 w-5" />
                    </button>
                  </div>

                  {/* Away */}
                  <div className="flex flex-col gap-3">
                    <TeamPanel team={awayTeam} side="away" />
                    <TeamCombobox
                      label="Away Team"
                      value={awayTeam}
                      onChange={(t) => { setAwayTeam(t); reset(); }}
                      teams={teams}
                      disabledTeam={homeTeam}
                      placeholder="Search away team…"
                    />
                  </div>
                </div>

                {/* Date + Stage */}
                <div className="flex flex-col sm:flex-row gap-3 border-t border-navy-600/60 pt-4">
                  <div className="flex-1 flex flex-col gap-1.5">
                    <label
                      htmlFor="match-date"
                      className="text-[11px] font-bold tracking-[0.2em] text-slate-500 uppercase"
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
                      className="rounded-lg bg-navy-700 border border-navy-600 text-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-fifa-blue [color-scheme:dark]"
                    />
                    {dateError && <p className="text-red-400 text-xs">{dateError}</p>}
                  </div>
                  <div className="flex-1">
                    <StageSelect value={stage} onChange={(s) => { setStage(s); reset(); }} />
                  </div>
                </div>

                <PredictButton
                  loading={predLoading}
                  disabled={!homeTeam || !awayTeam}
                  onClick={handlePredict}
                />
              </>
            )}
          </div>
        </div>

        {/* API error */}
        {error && (
          <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
            {error === "Failed to fetch"
              ? "Cannot connect to backend — make sure the FastAPI server is running on port 8000."
              : error}
          </div>
        )}

        {/* ── Results ──────────────────────────────────────────── */}
        {result && (() => {
          const p = result.probabilities;
          const dominant =
            p.home_win > p.draw && p.home_win > p.away_win ? "H" :
            p.away_win > p.draw && p.away_win > p.home_win ? "A" : "D";

          let predictedScore: [number, number] | null = null;
          if (result.top_scorelines.length > 0) {
            predictedScore = selectScoreline(
              dominant,
              result.top_scorelines,
              result.expected_goals?.home ?? 1,
              result.expected_goals?.away ?? 1,
            );
          }

          const homeDisplay = result.home_team === "United States" ? "USA" : result.home_team;
          const c = venueCity ? 1 : 0; // card delay offset when stadium card is shown
          const awayDisplay = result.away_team === "United States" ? "USA" : result.away_team;

          return (
            <motion.div
              key={`${result.home_team}-${result.away_team}-${result.match_date}`}
              ref={resultsRef}
              className="flex flex-col gap-4"
            >
              {/* Stadium card: shown when venue is known from the schedule */}
              {venueCity && (
                <motion.div custom={0} initial="hidden" animate="visible" variants={cardVariants}>
                  <StadiumCard venueCity={venueCity} />
                </motion.div>
              )}

              {/* Card 1: Stadium scoreboard */}
              <motion.div
                custom={venueCity ? 1 : 0}
                initial="hidden"
                animate="visible"
                variants={cardVariants}
                className="relative overflow-hidden rounded-2xl border border-navy-600 bg-navy-800"
              >
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-fifa-blue/50 to-transparent" />
                <div className="absolute inset-0 pointer-events-none">
                  <div className="absolute inset-y-0 left-0 w-2/5 bg-gradient-to-r from-fifa-blue/[0.09] to-transparent" />
                  <div className="absolute inset-y-0 right-0 w-2/5 bg-gradient-to-l from-gold-500/[0.09] to-transparent" />
                </div>

                <div className="relative z-10 p-6 sm:p-8">
                  {/* Match meta row */}
                  <div className="flex items-center justify-center gap-2 mb-8 flex-wrap">
                    <span className="text-[10px] font-bold tracking-[0.25em] text-fifa-blue uppercase">{stage}</span>
                    <span className="w-0.5 h-0.5 rounded-full bg-navy-600" />
                    <span className="text-[10px] text-slate-500 tracking-wider">{formatMatchDate(result.match_date)}</span>
                    <span className="w-0.5 h-0.5 rounded-full bg-navy-600" />
                    <span className="text-[10px] text-slate-600 tracking-wider uppercase">FIFA World Cup 2026</span>
                  </div>

                  {/* Teams + Score */}
                  <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 sm:gap-8">
                    {/* Home */}
                    <div className="flex flex-col items-center gap-3">
                      <motion.div
                        className="relative cursor-default"
                        whileHover={{ scale: 1.05 }}
                        transition={{ type: "spring", stiffness: 300, damping: 20 }}
                      >
                        <div className="absolute -inset-6 bg-fifa-blue rounded-3xl blur-2xl opacity-40" />
                        <div className="absolute -inset-1 bg-fifa-blue rounded-2xl blur-md opacity-20" />
                        <FlagIcon
                          team={result.home_team}
                          className="relative w-24 h-[64px] sm:w-40 sm:h-[107px] rounded-xl shadow-2xl"
                        />
                      </motion.div>
                      <div className="text-center">
                        <div className="font-anton text-xl sm:text-2xl text-white leading-none">{homeDisplay}</div>
                        <div className="text-[10px] font-bold tracking-[0.2em] text-fifa-blue uppercase mt-1">Home</div>
                      </div>
                    </div>

                    {/* Score */}
                    <div className="flex flex-col items-center gap-2">
                      {predictedScore ? (
                        <>
                          <div className="font-anton text-3xl sm:text-5xl text-white tracking-widest tabular-nums">
                            {predictedScore[0]}–{predictedScore[1]}
                          </div>
                          <div className="text-[9px] font-bold tracking-[0.3em] text-slate-600 uppercase">
                            Predicted
                          </div>
                        </>
                      ) : (
                        <div className="font-anton text-3xl text-navy-600">—</div>
                      )}
                    </div>

                    {/* Away */}
                    <div className="flex flex-col items-center gap-3">
                      <motion.div
                        className="relative cursor-default"
                        whileHover={{ scale: 1.05 }}
                        transition={{ type: "spring", stiffness: 300, damping: 20 }}
                      >
                        <div className="absolute -inset-6 bg-gold-500 rounded-3xl blur-2xl opacity-40" />
                        <div className="absolute -inset-1 bg-gold-500 rounded-2xl blur-md opacity-20" />
                        <FlagIcon
                          team={result.away_team}
                          className="relative w-24 h-[64px] sm:w-40 sm:h-[107px] rounded-xl shadow-2xl"
                        />
                      </motion.div>
                      <div className="text-center">
                        <div className="font-anton text-xl sm:text-2xl text-white leading-none">{awayDisplay}</div>
                        <div className="text-[10px] font-bold tracking-[0.2em] text-gold-500 uppercase mt-1">Away</div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Card 2: Analytics (WinnerCallout + ProbabilityBars + ExpectedGoals) */}
              <motion.div
                custom={c + 1}
                initial="hidden"
                animate="visible"
                variants={cardVariants}
                className="rounded-2xl border border-navy-600 bg-navy-800 overflow-hidden"
              >
                <div className="p-6 sm:p-8 flex flex-col gap-8">
                  <WinnerCallout
                    probabilities={result.probabilities}
                    homeTeam={result.home_team}
                    awayTeam={result.away_team}
                  />
                  <div className="h-px bg-navy-600" />
                  <ProbabilityBars
                    probabilities={result.probabilities}
                    homeTeam={result.home_team}
                    awayTeam={result.away_team}
                    confidence={result.confidence}
                  />
                  {result.expected_goals &&
                    (result.expected_goals.home > 0 || result.expected_goals.away > 0) && (
                      <>
                        <div className="h-px bg-navy-600" />
                        <ExpectedGoals
                          xg={result.expected_goals}
                          homeTeam={result.home_team}
                          awayTeam={result.away_team}
                        />
                      </>
                    )}
                </div>
              </motion.div>

              {/* Card 3: Scorelines */}
              {result.top_scorelines.length > 0 && (
                <motion.div
                  custom={c + 2}
                  initial="hidden"
                  animate="visible"
                  variants={cardVariants}
                  className="rounded-2xl border border-navy-600 bg-navy-800 p-6"
                >
                  <ScorelineGrid scorelines={result.top_scorelines} />
                </motion.div>
              )}

              {/* Card 4: Explanation */}
              <motion.div
                custom={c + 3}
                initial="hidden"
                animate="visible"
                variants={cardVariants}
                className="rounded-2xl border border-navy-600 bg-navy-800 p-6"
              >
                <ExplanationPanel
                  explanation={result.explanation}
                  homeTeam={result.home_team}
                  awayTeam={result.away_team}
                />
              </motion.div>

              {/* Metadata */}
              <motion.div custom={c + 4} initial="hidden" animate="visible" variants={cardVariants}>
                <MetadataBadge result={result} />
              </motion.div>
            </motion.div>
          );
        })()}
      </div>
    </main>
  );
}
