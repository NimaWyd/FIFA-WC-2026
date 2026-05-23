"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeftIcon, ChevronRightIcon, BoltIcon } from "@heroicons/react/24/solid";
import { WCGroup, WCMatch } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";
import GroupStandings, { Standing } from "@/components/GroupStandings";
import { predict } from "@/lib/api";
import { displayName } from "@/lib/utils";

interface Props {
  group: WCGroup;
  onBack: () => void;
  onPredict: (match: WCMatch) => void;
}

function formatDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function parseScoreline(s: string): [number, number] {
  const [h, a] = s.split("-").map(Number);
  return [h ?? 0, a ?? 0];
}

function buildStandings(
  teams: string[],
  results: Array<{ match: WCMatch; homeGoals: number; awayGoals: number }>
): Standing[] {
  const map: Record<string, Standing> = {};
  for (const t of teams) {
    map[t] = { team: t, played: 0, won: 0, drawn: 0, lost: 0, gf: 0, ga: 0, gd: 0, points: 0 };
  }
  for (const { match, homeGoals, awayGoals } of results) {
    const h = map[match.home];
    const a = map[match.away];
    if (!h || !a) continue;
    h.played++;
    a.played++;
    h.gf += homeGoals;
    h.ga += awayGoals;
    a.gf += awayGoals;
    a.ga += homeGoals;
    if (homeGoals > awayGoals) {
      h.won++; h.points += 3; a.lost++;
    } else if (homeGoals === awayGoals) {
      h.drawn++; h.points += 1; a.drawn++; a.points += 1;
    } else {
      a.won++; a.points += 3; h.lost++;
    }
    h.gd = h.gf - h.ga;
    a.gd = a.gf - a.ga;
  }
  return Object.values(map);
}

const HOSTS = new Set(["Mexico", "United States", "Canada"]);

// Matches are stored MD1/MD1/MD2/MD2/MD3/MD3
const MATCHDAY_SLICES: [number, number][] = [[0, 2], [2, 4], [4, 6]];

export default function GroupView({ group, onBack, onPredict }: Props) {
  const [standings, setStandings] = useState<Standing[] | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [predError, setPredError] = useState<string | null>(null);
  const [matchResults, setMatchResults] = useState<Record<string, {
    homeGoals: number; awayGoals: number;
    homeWinProb: number; drawProb: number; awayWinProb: number;
  }>>({});

  async function handlePredictAll() {
    setPredicting(true);
    setProgress(0);
    setPredError(null);
    setStandings(null);
    setMatchResults({});

    const results: Array<{ match: WCMatch; homeGoals: number; awayGoals: number }> = [];

    for (const match of group.matches) {
      try {
        const res = await predict({
          home_team: match.home,
          away_team: match.away,
          match_date: match.date,
          competition: "FIFA World Cup",
          neutral: true,
          tournament_stage: "Group Stage",
        });

        const p = res.probabilities;
        let homeGoals: number;
        let awayGoals: number;

        const dominant =
          p.home_win > p.draw && p.home_win > p.away_win ? "H" :
          p.away_win > p.draw && p.away_win > p.home_win ? "A" : "D";

        if (res.top_scorelines.length > 0) {
          const matching = res.top_scorelines.find((s) => {
            const [hg, ag] = parseScoreline(s.scoreline);
            if (hg + ag > 4) return false;
            if (dominant === "H") return hg > ag;
            if (dominant === "A") return ag > hg;
            return hg === ag;
          });
          if (matching) {
            [homeGoals, awayGoals] = parseScoreline(matching.scoreline);
          } else {
            if (dominant === "H") { homeGoals = 1; awayGoals = 0; }
            else if (dominant === "A") { homeGoals = 0; awayGoals = 1; }
            else { homeGoals = 1; awayGoals = 1; }
          }
        } else if (res.expected_goals) {
          homeGoals = Math.round(res.expected_goals.home);
          awayGoals = Math.round(res.expected_goals.away);
          if (dominant === "H" && homeGoals <= awayGoals) homeGoals = awayGoals + 1;
          if (dominant === "A" && awayGoals <= homeGoals) awayGoals = homeGoals + 1;
          if (dominant === "D") homeGoals = awayGoals = Math.round((homeGoals + awayGoals) / 2);
        } else {
          if (dominant === "H") { homeGoals = 1; awayGoals = 0; }
          else if (dominant === "A") { homeGoals = 0; awayGoals = 1; }
          else { homeGoals = 1; awayGoals = 1; }
        }

        results.push({ match, homeGoals, awayGoals });
        setMatchResults((prev) => ({
          ...prev,
          [`${match.home}|${match.away}`]: {
            homeGoals, awayGoals,
            homeWinProb: p.home_win,
            drawProb: p.draw,
            awayWinProb: p.away_win,
          },
        }));
        setProgress((prev) => prev + 1);
      } catch {
        setPredError("Prediction failed — is the backend running?");
        setPredicting(false);
        return;
      }
    }

    setStandings(buildStandings(group.teams, results));
    setPredicting(false);
  }

  return (
    <div className="flex flex-col gap-6">
      {/* ── Group hero banner ───────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-navy-700/80 to-navy-900 border border-navy-600 p-4 sm:p-6">
        {/* Top shimmer line */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-fifa-blue/50 to-transparent" />

        {/* Backdrop group letter */}
        <span className="pointer-events-none select-none absolute right-6 top-1/2 -translate-y-1/2 font-anton text-[180px] leading-none text-white/[0.04]">
          {group.id}
        </span>

        {/* ── Mobile layout: stacked ── */}
        <div className="sm:hidden relative z-10 flex flex-col gap-3">
          {/* Back + Predict All row */}
          <div className="flex items-center justify-between">
            <button
              onClick={onBack}
              className="p-2 rounded-xl bg-navy-900/70 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue/50 transition-all"
            >
              <ArrowLeftIcon className="h-4 w-4" />
            </button>
            <button
              onClick={handlePredictAll}
              disabled={predicting}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-fifa-blue text-white text-sm font-bold hover:bg-fifa-blue/90 shadow-[0_4px_20px_rgba(26,63,255,0.4)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {predicting ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {progress}/6
                </>
              ) : (
                <>
                  <BoltIcon className="h-4 w-4" />
                  Predict All
                </>
              )}
            </button>
          </div>

          {/* Eyebrow + heading */}
          <div>
            <p className="text-[10px] font-bold tracking-[0.2em] text-fifa-blue uppercase mb-1">
              FIFA World Cup 2026
            </p>
            <h2 className="font-anton text-[44px] text-white uppercase tracking-wide leading-none">
              Group {group.id}
            </h2>
          </div>

          {/* Team names — whitespace-nowrap prevents mid-word wrapping */}
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {group.teams.map((t, i) => (
              <span key={t} className="flex items-center gap-1.5 text-sm text-slate-400 whitespace-nowrap">
                {i > 0 && <span className="w-1 h-1 rounded-full bg-navy-500 inline-block" />}
                {displayName(t)}
                {HOSTS.has(t) && (
                  <span className="text-[9px] font-bold text-gold-500 ml-0.5">★ HOST</span>
                )}
              </span>
            ))}
          </div>

          {/* Progress bar */}
          {predicting && (
            <div className="flex items-center gap-3">
              <div className="flex-1 h-1 bg-navy-900 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-fifa-blue to-fifa-blue-light rounded-full"
                  initial={{ width: "0%" }}
                  animate={{ width: `${(progress / 6) * 100}%` }}
                  transition={{ duration: 0.35, ease: "easeOut" }}
                />
              </div>
              <span className="text-[11px] text-slate-500 tabular-nums w-14 text-right">
                {progress} of 6
              </span>
            </div>
          )}
        </div>

        {/* ── Desktop layout: 3-column row ── */}
        <div className="hidden sm:block relative z-10">
          <div className="flex items-start gap-4">
            {/* Back button */}
            <button
              onClick={onBack}
              className="mt-1 p-2.5 rounded-xl bg-navy-900/70 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue/50 transition-all flex-shrink-0"
            >
              <ArrowLeftIcon className="h-4 w-4" />
            </button>

            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-bold tracking-[0.3em] text-fifa-blue uppercase mb-1">
                FIFA World Cup 2026
              </p>
              <h2 className="font-anton text-5xl sm:text-6xl text-white uppercase tracking-wide leading-none">
                Group {group.id}
              </h2>
              <div className="flex flex-wrap gap-x-2 gap-y-1 mt-3">
                {group.teams.map((t, i) => (
                  <span key={t} className="flex items-center gap-2 text-sm text-slate-400">
                    {i > 0 && <span className="w-0.5 h-0.5 rounded-full bg-navy-500" />}
                    {displayName(t)}
                    {HOSTS.has(t) && (
                      <span className="text-[9px] font-bold text-gold-500">★ HOST</span>
                    )}
                  </span>
                ))}
              </div>
            </div>

            {/* Predict All button */}
            <button
              onClick={handlePredictAll}
              disabled={predicting}
              className="flex-shrink-0 flex items-center gap-2 px-5 py-2.5 rounded-xl bg-fifa-blue text-white text-sm font-bold hover:bg-fifa-blue/90 shadow-[0_4px_20px_rgba(26,63,255,0.4)] hover:shadow-[0_4px_28px_rgba(26,63,255,0.65)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {predicting ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {progress}/6
                </>
              ) : (
                <>
                  <BoltIcon className="h-4 w-4" />
                  Predict All
                </>
              )}
            </button>
          </div>

          {/* Progress bar */}
          {predicting && (
            <div className="mt-4 ml-14">
              <div className="flex items-center gap-3">
                <div className="flex-1 h-1 bg-navy-900 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-fifa-blue to-fifa-blue-light rounded-full"
                    initial={{ width: "0%" }}
                    animate={{ width: `${(progress / 6) * 100}%` }}
                    transition={{ duration: 0.35, ease: "easeOut" }}
                  />
                </div>
                <span className="text-[11px] text-slate-500 tabular-nums w-16 text-right">
                  {progress} of 6
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Error ───────────────────────────────────────────────── */}
      {predError && (
        <div className="bg-red-950/60 border border-red-800/60 rounded-xl px-4 py-3 text-red-300 text-sm">
          {predError}
        </div>
      )}

      {/* ── Standings ───────────────────────────────────────────── */}
      <AnimatePresence>
        {standings && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <GroupStandings standings={standings} groupId={group.id} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Teams strip ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {group.teams.map((team) => (
          <div
            key={team}
            className={`flex flex-col items-center gap-2.5 p-4 rounded-xl border transition-colors ${
              HOSTS.has(team)
                ? "bg-gold-500/5 border-gold-500/20"
                : "bg-navy-800 border-navy-600"
            }`}
          >
            <FlagIcon team={team} className="w-14 h-9 rounded shadow-md" />
            <span className="text-xs font-semibold text-slate-200 text-center leading-tight">
              {displayName(team)}
            </span>
            {HOSTS.has(team) && (
              <span className="text-[9px] font-bold tracking-widest text-gold-500 uppercase">
                Host Nation
              </span>
            )}
          </div>
        ))}
      </div>

      {/* ── Fixtures ────────────────────────────────────────────── */}
      <div>
        <h3 className="text-[11px] font-bold tracking-[0.22em] text-slate-500 uppercase mb-4">
          Fixtures
        </h3>

        <div className="flex flex-col gap-5">
          {MATCHDAY_SLICES.map(([start, end], mdIdx) => {
            const mdMatches = group.matches.slice(start, end);
            return (
              <div key={mdIdx}>
                {/* Matchday divider */}
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-[10px] font-bold tracking-[0.25em] text-fifa-blue uppercase flex-shrink-0">
                    Matchday {mdIdx + 1}
                  </span>
                  <div className="flex-1 h-px bg-navy-600" />
                </div>

                <div className="flex flex-col gap-2">
                  {mdMatches.map((match) => {
                    const matchKey = `${match.home}|${match.away}`;
                    const mr = matchResults[matchKey];

                    return (
                      <div
                        key={matchKey}
                        className="group relative bg-navy-800 border border-navy-600 rounded-xl overflow-hidden hover:border-navy-500 transition-colors"
                      >
                        {/* Hover shimmer on top edge */}
                        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-fifa-blue/0 to-transparent group-hover:via-fifa-blue/40 transition-all duration-500" />

                        {/* ── Mobile layout: 2-row ── */}
                        <div className="sm:hidden flex flex-col gap-2 px-4 py-3">
                          {/* Row 1: Flag · Name · VS/score · Name · Flag */}
                          <div className="flex items-center gap-2">
                            <FlagIcon
                              team={match.home}
                              className="w-7 h-5 rounded-sm shadow-sm flex-shrink-0"
                            />
                            <span className="flex-1 min-w-0 text-sm font-semibold text-white truncate">
                              {displayName(match.home)}
                            </span>

                            {mr ? (
                              <div className="flex flex-col items-center flex-shrink-0 px-1 gap-0.5">
                                <span className="text-[12px] font-bold text-white tabular-nums">
                                  {mr.homeGoals}–{mr.awayGoals}
                                </span>
                                <div className="flex w-10 h-0.5 rounded-full overflow-hidden">
                                  <div className="bg-blue-400/80" style={{ width: `${Math.round(mr.homeWinProb * 100)}%` }} />
                                  <div className="bg-slate-500/50" style={{ width: `${Math.round(mr.drawProb * 100)}%` }} />
                                  <div className="bg-red-400/70" style={{ width: `${Math.round(mr.awayWinProb * 100)}%` }} />
                                </div>
                              </div>
                            ) : (
                              <span className="flex-shrink-0 text-[11px] font-bold text-navy-500 bg-navy-900 px-2 py-0.5 rounded border border-navy-600">
                                VS
                              </span>
                            )}

                            <span className="flex-1 min-w-0 text-sm font-semibold text-white text-right truncate">
                              {displayName(match.away)}
                            </span>
                            <FlagIcon
                              team={match.away}
                              className="w-7 h-5 rounded-sm shadow-sm flex-shrink-0"
                            />
                          </div>

                          {/* Row 2: Date · Predict button */}
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] text-slate-500">{formatDate(match.date)}</span>
                            <button
                              onClick={() => onPredict(match)}
                              className="flex items-center gap-1 px-3 py-1 rounded-lg bg-fifa-blue/10 border border-fifa-blue/20 text-fifa-blue-light text-xs font-semibold hover:bg-fifa-blue/20 hover:border-fifa-blue/50 transition-all"
                            >
                              Predict
                              <ChevronRightIcon className="h-3 w-3" />
                            </button>
                          </div>
                        </div>

                        {/* ── Desktop layout: single row ── */}
                        <div className="hidden sm:flex items-center px-4 py-3 gap-3">
                          {/* Date / venue */}
                          <div className="w-16 flex-shrink-0 text-center">
                            <div className="text-xs font-semibold text-slate-300">
                              {formatDate(match.date)}
                            </div>
                            <div className="text-[10px] text-slate-600 mt-0.5 truncate">
                              {match.venue}
                            </div>
                          </div>

                          {/* Home team */}
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <FlagIcon
                              team={match.home}
                              className="w-7 h-5 rounded-sm shadow-sm flex-shrink-0"
                            />
                            <span className="text-sm font-semibold text-white truncate">
                              {displayName(match.home)}
                            </span>
                          </div>

                          {/* Winner / VS */}
                          {mr ? (
                            <div className="flex-shrink-0 flex flex-col items-center gap-1.5 w-28">
                              {(() => {
                                const hw = mr.homeWinProb;
                                const dw = mr.drawProb;
                                const aw = mr.awayWinProb;
                                const isDraw = dw >= hw && dw >= aw;
                                const winner = hw >= aw ? match.home : match.away;
                                const winProb = Math.round((isDraw ? dw : Math.max(hw, aw)) * 100);
                                return (
                                  <>
                                    {isDraw ? (
                                      <span className="text-[11px] font-bold text-slate-300 bg-navy-900/80 px-2.5 py-1 rounded-lg border border-navy-500 whitespace-nowrap">
                                        Draw · {winProb}%
                                      </span>
                                    ) : (
                                      <div className="flex items-center gap-1.5 bg-navy-900/80 px-2 py-1 rounded-lg border border-fifa-blue/40 shadow-[0_0_10px_rgba(26,63,255,0.15)]">
                                        <FlagIcon team={winner} className="w-5 h-3.5 rounded-sm shadow-sm flex-shrink-0" />
                                        <span className="text-[12px] font-bold text-white tabular-nums">{winProb}%</span>
                                      </div>
                                    )}
                                    <div className="flex w-full h-1 rounded-full overflow-hidden">
                                      <div className="bg-blue-400/80 transition-all" style={{ width: `${Math.round(hw * 100)}%` }} />
                                      <div className="bg-slate-500/50 transition-all" style={{ width: `${Math.round(dw * 100)}%` }} />
                                      <div className="bg-red-400/70 transition-all" style={{ width: `${Math.round(aw * 100)}%` }} />
                                    </div>
                                  </>
                                );
                              })()}
                            </div>
                          ) : (
                            <div className="flex-shrink-0 flex flex-col items-center gap-0.5 w-14">
                              <span className="text-[11px] font-bold text-navy-500 bg-navy-900 px-2.5 py-1 rounded-lg border border-navy-600">
                                VS
                              </span>
                            </div>
                          )}

                          {/* Away team */}
                          <div className="flex items-center gap-2 flex-1 justify-end min-w-0">
                            <span className="text-sm font-semibold text-white truncate text-right">
                              {displayName(match.away)}
                            </span>
                            <FlagIcon
                              team={match.away}
                              className="w-7 h-5 rounded-sm shadow-sm flex-shrink-0"
                            />
                          </div>

                          {/* Predict button */}
                          <button
                            onClick={() => onPredict(match)}
                            className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-fifa-blue/10 border border-fifa-blue/20 text-fifa-blue-light text-xs font-semibold hover:bg-fifa-blue/20 hover:border-fifa-blue/50 transition-all"
                          >
                            Predict
                            <ChevronRightIcon className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
