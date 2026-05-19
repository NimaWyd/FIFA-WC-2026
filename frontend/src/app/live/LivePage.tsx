"use client";

import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";
import StadiumCard from "@/components/StadiumCard";
import { WC2026_GROUPS } from "@/lib/wc2026Groups";
import { WC2026_STADIUMS } from "@/lib/wc2026Stadiums";
import { useLiveMatches } from "@/hooks/useLiveMatches";
import type { LiveMatch, LiveMatchesResponse } from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

interface StaticMatch {
  home: string;
  away: string;
  date: string;
  venue: string;
  group: string;
  matchday: number;
}

interface MergedMatch {
  static: StaticMatch;
  live?: LiveMatch;
}

type DisplayStatus = "live" | "ht" | "ft" | "upcoming" | "today" | "postponed";

interface TeamStanding {
  team: string;
  p: number;
  w: number;
  d: number;
  l: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
}

// ─── Static data ─────────────────────────────────────────────────────────────

const ALL_STATIC: StaticMatch[] = WC2026_GROUPS.flatMap((g) =>
  g.matches.map((m, i) => ({
    ...m,
    group: g.id,
    matchday: Math.floor(i / 2) + 1,
  }))
);

const UNIQUE_DATES = Array.from(new Set(ALL_STATIC.map((m) => m.date))).sort();

// ─── Helpers ─────────────────────────────────────────────────────────────────

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function defaultDate() {
  const today = todayStr();
  return UNIQUE_DATES.find((d) => d >= today) ?? UNIQUE_DATES[UNIQUE_DATES.length - 1];
}

function fmtDateTab(iso: string) {
  const d = new Date(iso + "T12:00:00Z");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

function fmtDateHeading(iso: string) {
  const d = new Date(iso + "T12:00:00Z");
  return d.toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC",
  });
}

function fmtTime(utcDate: string) {
  return new Date(utcDate).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function getDisplayStatus(live: LiveMatch | undefined, date: string): DisplayStatus {
  if (live) {
    if (live.status === "IN_PLAY") return "live";
    if (live.status === "PAUSED") return "ht";
    if (live.status === "FINISHED") return "ft";
    if (
      live.status === "POSTPONED" ||
      live.status === "SUSPENDED" ||
      live.status === "CANCELLED"
    )
      return "postponed";
  }
  const today = todayStr();
  if (date === today) return "today";
  if (date < today) return "ft";
  return "upcoming";
}

// ─── Countdown ────────────────────────────────────────────────────────────────

function useCountdown(targetIso: string) {
  const [parts, setParts] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0, done: false });

  useEffect(() => {
    function tick() {
      const diff = new Date(targetIso).getTime() - Date.now();
      if (diff <= 0) {
        setParts({ days: 0, hours: 0, minutes: 0, seconds: 0, done: true });
        return;
      }
      setParts({
        days: Math.floor(diff / 86400000),
        hours: Math.floor((diff % 86400000) / 3600000),
        minutes: Math.floor((diff % 3600000) / 60000),
        seconds: Math.floor((diff % 60000) / 1000),
        done: false,
      });
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [targetIso]);

  return parts;
}

function CountdownTimer({ data }: { data: LiveMatchesResponse | null }) {
  const target = useMemo(() => {
    if (data?.matches) {
      const next = data.matches.find(
        (m) => m.status === "TIMED" || m.status === "SCHEDULED"
      );
      if (next?.utc_date) return next.utc_date;
    }
    return "2026-06-11T00:00:00Z";
  }, [data]);

  const { days, hours, minutes, seconds, done } = useCountdown(target);

  if (done) return null;

  const tournamentStarted = todayStr() >= "2026-06-11";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="flex flex-col items-center gap-5"
    >
      <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-slate-500">
        {tournamentStarted ? "Next kickoff" : "Tournament starts in"}
      </p>
      <div className="flex items-end gap-2 sm:gap-3">
        {[
          { v: days, label: "DAYS" },
          { v: hours, label: "HRS" },
          { v: minutes, label: "MIN" },
          { v: seconds, label: "SEC" },
        ].map(({ v, label }, i) => (
          <div key={label} className="flex items-end gap-2 sm:gap-3">
            {i > 0 && (
              <span className="text-slate-700 font-bold text-2xl sm:text-3xl mb-3 leading-none select-none">:</span>
            )}
            <div className="flex flex-col items-center gap-1.5">
              <div className="relative w-[60px] sm:w-[72px] h-[60px] sm:h-[72px] flex items-center justify-center rounded-xl bg-navy-800 border border-navy-700 shadow-xl shadow-black/40 overflow-hidden">
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-navy-600 to-transparent" />
                <div className="absolute inset-0 bg-gradient-to-b from-white/[0.025] to-transparent" />
                <span className="font-anton text-[28px] sm:text-[34px] text-white tabular-nums leading-none">
                  {String(v).padStart(2, "0")}
                </span>
              </div>
              <span className="text-[8px] sm:text-[9px] font-bold tracking-[0.25em] text-slate-600 uppercase">
                {label}
              </span>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

// ─── Today strip ──────────────────────────────────────────────────────────────

function TodayStrip({ liveByKey }: { liveByKey: Map<string, LiveMatch> }) {
  const today = todayStr();
  let label = "TODAY";
  let stripDate = today;
  let stripMatches = ALL_STATIC.filter((m) => m.date === today);

  if (stripMatches.length === 0) {
    const nextDate = UNIQUE_DATES.find((d) => d > today);
    if (!nextDate) return null;
    label = "NEXT UP";
    stripDate = nextDate;
    stripMatches = ALL_STATIC.filter((m) => m.date === nextDate);
  }

  if (stripMatches.length === 0) return null;

  const isToday = label === "TODAY";

  return (
    <div className="border-b border-navy-700 bg-navy-900/90 backdrop-blur-md">
      <div className="max-w-screen-xl mx-auto px-4 md:px-6">
        <div
          className="flex items-center gap-3 py-2.5 overflow-x-auto scrollbar-none"
          style={{ scrollbarWidth: "none" }}
        >
          {/* Label chip */}
          <div className="shrink-0 flex items-center gap-2.5">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-bold tracking-[0.2em] uppercase border ${
                isToday
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/25"
                  : "bg-fifa-blue/10 text-[#6b93ff] border-fifa-blue/25"
              }`}
            >
              {isToday && (
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              )}
              {label}
            </span>
            {!isToday && (
              <span className="text-[10px] text-slate-600 shrink-0">{fmtDateTab(stripDate)}</span>
            )}
            <div className="w-px h-5 bg-navy-700 shrink-0" />
          </div>

          {/* Match pills */}
          <div className="flex items-center gap-2">
            {stripMatches.map((m) => {
              const live =
                liveByKey.get(`${m.home}|${m.away}`) ??
                liveByKey.get(`${m.away}|${m.home}`);
              const status = getDisplayStatus(live, m.date);
              const isLiveMatch = status === "live" || status === "ht";
              const isFt = status === "ft" && live && live.home_score != null;
              const showScore = isLiveMatch || isFt;

              return (
                <div
                  key={`${m.home}|${m.away}`}
                  className={`shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[11px] ${
                    isLiveMatch
                      ? "bg-emerald-500/[0.07] border-emerald-500/20"
                      : "bg-navy-800/50 border-navy-700/50"
                  }`}
                >
                  <FlagIcon team={m.home} className="w-[18px] h-[11px] rounded-[2px] shrink-0" />
                  <span className="font-bold text-slate-200 uppercase tracking-[0.05em]">
                    {m.home}
                  </span>

                  {showScore ? (
                    <>
                      <span
                        className={`font-bold tabular-nums ${isLiveMatch ? "text-emerald-400" : "text-white"}`}
                      >
                        {live!.home_score ?? 0}
                      </span>
                      <span className="text-slate-600 text-[10px] font-bold">–</span>
                      <span
                        className={`font-bold tabular-nums ${isLiveMatch ? "text-emerald-400" : "text-white"}`}
                      >
                        {live!.away_score ?? 0}
                      </span>
                    </>
                  ) : (
                    <span className="text-slate-600 font-bold text-[10px] px-1">
                      {live?.utc_date ? fmtTime(live.utc_date) : "vs"}
                    </span>
                  )}

                  <span className="font-bold text-slate-200 uppercase tracking-[0.05em]">
                    {m.away}
                  </span>
                  <FlagIcon team={m.away} className="w-[18px] h-[11px] rounded-[2px] shrink-0" />

                  {status === "ht" && (
                    <span className="text-[9px] font-bold text-amber-400 ml-0.5">HT</span>
                  )}
                  {isLiveMatch && status !== "ht" && (
                    <span className="text-[9px] font-bold text-emerald-400 ml-0.5 animate-pulse">
                      {live?.minute != null ? `${live.minute}'` : "LIVE"}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status, minute }: { status: DisplayStatus; minute?: number | null }) {
  if (status === "live") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-bold uppercase tracking-[0.18em] bg-emerald-500/12 text-emerald-400 border border-emerald-500/25">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        {minute != null ? `${minute}'` : "LIVE"}
      </span>
    );
  }
  if (status === "ht") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-bold uppercase tracking-[0.18em] bg-amber-500/12 text-amber-400 border border-amber-500/25">
        HALF TIME
      </span>
    );
  }
  if (status === "ft") {
    return (
      <span className="px-2.5 py-1 rounded-full text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500 bg-navy-700/80 border border-navy-600/60">
        FULL TIME
      </span>
    );
  }
  if (status === "today") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-bold uppercase tracking-[0.18em] bg-fifa-blue/10 text-[#6b93ff] border border-fifa-blue/25">
        <span className="w-1.5 h-1.5 rounded-full bg-[#6b93ff]" />
        TODAY
      </span>
    );
  }
  if (status === "postponed") {
    return (
      <span className="px-2.5 py-1 rounded-full text-[9px] font-bold uppercase tracking-[0.18em] text-red-400 bg-red-950/30 border border-red-800/35">
        POSTPONED
      </span>
    );
  }
  return null;
}

// ─── Venue detail (expanded) ──────────────────────────────────────────────────

function VenueDetail({ city }: { city: string }) {
  if (WC2026_STADIUMS[city]) {
    return <StadiumCard venueCity={city} />;
  }
  return (
    <div className="rounded-xl border border-navy-700/60 bg-navy-800/50 px-5 py-4 text-center text-sm text-slate-500">
      Venue details not available for {city}
    </div>
  );
}

// ─── Broadcast match card ─────────────────────────────────────────────────────

function MatchCard({
  match,
  expanded,
  onToggle,
}: {
  match: MergedMatch;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { static: s, live } = match;
  const status = getDisplayStatus(live, s.date);
  const hasScore = live && (live.home_score != null || live.away_score != null);
  const isLive = status === "live" || status === "ht";
  const isFinished = status === "ft" && !!hasScore;
  const showScore = isLive || isFinished;

  const homeScore = live?.home_score ?? 0;
  const awayScore = live?.away_score ?? 0;
  const homeWins = isFinished && homeScore > awayScore;
  const awayWins = isFinished && awayScore > homeScore;
  const isDraw = isFinished && homeScore === awayScore;

  const accentClass = isLive
    ? "bg-emerald-400"
    : status === "today"
    ? "bg-[#1a3fff]"
    : isFinished
    ? "bg-navy-600"
    : "bg-navy-700";

  const borderClass = isLive
    ? "border-emerald-500/25"
    : status === "today"
    ? "border-fifa-blue/20"
    : "border-navy-700/50";

  const venueCity = live?.venue ?? s.venue;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
      className={`rounded-xl border overflow-hidden ${borderClass} ${
        isLive ? "shadow-[0_0_24px_rgba(52,211,153,0.06)]" : ""
      }`}
    >
      {/* Accent top bar */}
      <div className={`h-[3px] ${accentClass}`} />

      {/* Clickable card header + body */}
      <button
        onClick={onToggle}
        className="w-full text-left bg-navy-800 transition-colors hover:bg-white/[0.015] focus-visible:outline-none"
      >
        {/* Header row */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-navy-700/40">
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold uppercase tracking-[0.22em] text-slate-500">
              GRP {s.group}
            </span>
            <span className="text-navy-600 select-none">·</span>
            <span className="text-[9px] text-slate-600 uppercase tracking-[0.14em]">
              MD {s.matchday}
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            <StatusBadge status={status} minute={live?.minute} />
            <svg
              className={`w-3 h-3 text-slate-600 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M2 4l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>

        {/* Score / teams */}
        <div className="px-4 py-4">
          {showScore ? (
            /* Broadcast horizontal layout with score chips */
            <div className="flex items-center gap-2">
              {/* Home */}
              <div
                className={`flex-1 flex items-center gap-2 min-w-0 ${
                  awayWins ? "opacity-45" : ""
                }`}
              >
                <FlagIcon
                  team={s.home}
                  className="w-8 h-5 rounded-[3px] shrink-0 shadow-sm"
                />
                <span
                  className={`font-bold text-[12px] uppercase tracking-[0.07em] truncate leading-tight ${
                    homeWins
                      ? "text-white"
                      : isDraw
                      ? "text-slate-200"
                      : "text-slate-400"
                  }`}
                >
                  {s.home}
                </span>
              </div>

              {/* Score chips */}
              <div className="flex items-center gap-1.5 shrink-0">
                <div
                  className={`w-10 h-10 flex items-center justify-center rounded-lg font-anton text-[22px] tabular-nums border ${
                    homeWins
                      ? "bg-pitch-400/12 text-pitch-300 border-pitch-400/25"
                      : "bg-navy-700/70 text-slate-200 border-navy-600/60"
                  }`}
                >
                  {homeScore}
                </div>
                <span className="text-slate-600 font-bold text-sm select-none">–</span>
                <div
                  className={`w-10 h-10 flex items-center justify-center rounded-lg font-anton text-[22px] tabular-nums border ${
                    awayWins
                      ? "bg-pitch-400/12 text-pitch-300 border-pitch-400/25"
                      : "bg-navy-700/70 text-slate-200 border-navy-600/60"
                  }`}
                >
                  {awayScore}
                </div>
              </div>

              {/* Away */}
              <div
                className={`flex-1 flex items-center gap-2 min-w-0 justify-end ${
                  homeWins ? "opacity-45" : ""
                }`}
              >
                <span
                  className={`font-bold text-[12px] uppercase tracking-[0.07em] truncate leading-tight text-right ${
                    awayWins
                      ? "text-white"
                      : isDraw
                      ? "text-slate-200"
                      : "text-slate-400"
                  }`}
                >
                  {s.away}
                </span>
                <FlagIcon
                  team={s.away}
                  className="w-8 h-5 rounded-[3px] shrink-0 shadow-sm"
                />
              </div>
            </div>
          ) : (
            /* Upcoming — vertical layout */
            <div className="space-y-1.5">
              <div className="flex items-center gap-2.5">
                <FlagIcon team={s.home} className="w-7 h-[18px] rounded-[3px] shrink-0" />
                <span className="font-bold text-[13px] uppercase tracking-[0.07em] text-slate-200 truncate">
                  {s.home}
                </span>
              </div>
              <div className="flex items-center gap-2 py-0.5">
                <div className="flex-1 h-px bg-navy-700/50" />
                <span className="text-[11px] text-slate-600 tabular-nums font-mono">
                  {live?.utc_date ? fmtTime(live.utc_date) : "TBD"}
                </span>
                <div className="flex-1 h-px bg-navy-700/50" />
              </div>
              <div className="flex items-center gap-2.5">
                <FlagIcon team={s.away} className="w-7 h-[18px] rounded-[3px] shrink-0" />
                <span className="font-bold text-[13px] uppercase tracking-[0.07em] text-slate-200 truncate">
                  {s.away}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 pb-3 flex items-center justify-between gap-2">
          <span className="text-[10px] text-slate-600 truncate flex items-center gap-1.5">
            <svg
              className="w-2.5 h-2.5 shrink-0"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <circle cx="6" cy="4.5" r="1.75" />
              <path
                d="M6 1C3.79 1 2 2.8 2 5c0 3 4 7 4 7s4-4 4-7c0-2.2-1.79-4-4-4z"
                strokeLinejoin="round"
              />
            </svg>
            {venueCity}
          </span>
          {isFinished && live?.halftime_home != null && (
            <span className="text-[10px] text-slate-600 shrink-0 font-mono">
              HT {live.halftime_home}–{live.halftime_away}
            </span>
          )}
          {isLive && live?.minute != null && live.minute > 45 && (
            <span className="text-[10px] text-emerald-600 font-medium shrink-0">2nd half</span>
          )}
        </div>
      </button>

      {/* Expanded — venue detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            key="expanded"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-navy-700/40 p-4">
              <VenueDetail city={venueCity} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── Group standings ──────────────────────────────────────────────────────────

function computeStandings(
  groupId: string,
  liveByKey: Map<string, LiveMatch>
): TeamStanding[] {
  const group = WC2026_GROUPS.find((g) => g.id === groupId);
  if (!group) return [];

  const map = new Map<string, TeamStanding>();
  for (const team of group.teams) {
    map.set(team, { team, p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, gd: 0, pts: 0 });
  }

  for (const match of group.matches) {
    const live =
      liveByKey.get(`${match.home}|${match.away}`) ??
      liveByKey.get(`${match.away}|${match.home}`);
    if (
      !live ||
      live.status !== "FINISHED" ||
      live.home_score == null ||
      live.away_score == null
    )
      continue;

    const home = map.get(match.home)!;
    const away = map.get(match.away)!;
    const hg = live.home_score;
    const ag = live.away_score;

    home.p++;
    home.gf += hg;
    home.ga += ag;
    home.gd += hg - ag;
    away.p++;
    away.gf += ag;
    away.ga += hg;
    away.gd += ag - hg;

    if (hg > ag) {
      home.w++;
      home.pts += 3;
      away.l++;
    } else if (ag > hg) {
      away.w++;
      away.pts += 3;
      home.l++;
    } else {
      home.d++;
      home.pts++;
      away.d++;
      away.pts++;
    }
  }

  return Array.from(map.values()).sort(
    (a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf
  );
}

function GroupStandingsTable({
  groupId,
  liveByKey,
}: {
  groupId: string;
  liveByKey: Map<string, LiveMatch>;
}) {
  const rows = computeStandings(groupId, liveByKey);

  return (
    <div className="rounded-xl border border-navy-700/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-navy-800 border-b border-navy-700/40">
        <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-400">
          Group {groupId}
        </span>
        <div className="flex items-center gap-3 sm:gap-4 text-[9px] font-bold uppercase tracking-[0.15em] text-slate-600">
          <span className="w-4 text-center">P</span>
          <span className="w-4 text-center">W</span>
          <span className="w-4 text-center">D</span>
          <span className="w-4 text-center">L</span>
          <span className="w-6 text-center">GD</span>
          <span className="w-6 text-center font-bold text-slate-500">PTS</span>
        </div>
      </div>

      {rows.map((row, i) => (
        <div
          key={row.team}
          className={`flex items-center px-4 py-2.5 border-b border-navy-700/25 last:border-0 transition-colors ${
            i < 2 ? "bg-pitch-400/[0.025]" : "bg-navy-800/40"
          }`}
        >
          {/* Pos */}
          <span
            className={`text-[10px] font-bold w-3.5 shrink-0 ${
              i < 2 ? "text-pitch-400" : "text-slate-700"
            }`}
          >
            {i + 1}
          </span>

          {/* Team */}
          <div className="flex items-center gap-2 flex-1 min-w-0 ml-3">
            {i < 2 && (
              <div className="w-[3px] h-4 rounded-full bg-pitch-400 shrink-0 -ml-1" />
            )}
            <FlagIcon team={row.team} className="w-[18px] h-[11px] rounded-[2px] shrink-0" />
            <span
              className={`text-[12px] font-semibold truncate ${
                i < 2 ? "text-white" : "text-slate-400"
              }`}
            >
              {row.team}
            </span>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-3 sm:gap-4 shrink-0">
            <span className="w-4 text-center text-[11px] tabular-nums text-slate-600">{row.p}</span>
            <span className="w-4 text-center text-[11px] tabular-nums text-slate-500">{row.w}</span>
            <span className="w-4 text-center text-[11px] tabular-nums text-slate-500">{row.d}</span>
            <span className="w-4 text-center text-[11px] tabular-nums text-slate-500">{row.l}</span>
            <span
              className={`w-6 text-center text-[11px] tabular-nums font-semibold ${
                row.gd > 0 ? "text-pitch-400" : row.gd < 0 ? "text-red-400" : "text-slate-600"
              }`}
            >
              {row.gd > 0 ? `+${row.gd}` : row.gd}
            </span>
            <span
              className={`w-6 text-center text-[12px] tabular-nums font-bold ${
                i < 2 ? "text-white" : "text-slate-400"
              }`}
            >
              {row.pts}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Date navigation ──────────────────────────────────────────────────────────

function DateNav({
  dates,
  selected,
  onSelect,
  today,
}: {
  dates: string[];
  selected: string;
  onSelect: (d: string) => void;
  today: string;
}) {
  const activeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
  }, [selected]);

  return (
    <div
      className="flex items-center gap-1 overflow-x-auto scrollbar-none"
      style={{ scrollbarWidth: "none" }}
    >
      {dates.map((d) => {
        const isSelected = d === selected;
        const isToday = d === today;
        return (
          <button
            key={d}
            ref={isSelected ? activeRef : undefined}
            onClick={() => onSelect(d)}
            className={`shrink-0 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-colors whitespace-nowrap uppercase tracking-[0.08em] ${
              isSelected
                ? "bg-fifa-blue text-white shadow-sm shadow-fifa-blue/25"
                : isToday
                ? "text-pitch-400 bg-pitch-400/10 border border-pitch-400/25 hover:bg-pitch-400/18"
                : "text-slate-500 hover:text-slate-300 hover:bg-navy-700"
            }`}
          >
            {isToday ? "Today" : fmtDateTab(d)}
          </button>
        );
      })}
    </div>
  );
}

// ─── Refresh bar ──────────────────────────────────────────────────────────────

function RefreshBar({
  lastRefresh,
  onRefresh,
  loading,
  hasLive,
  source,
}: {
  lastRefresh: Date | null;
  onRefresh: () => void;
  loading: boolean;
  hasLive: boolean;
  source?: string;
}) {
  return (
    <div className="flex items-center justify-between text-xs text-slate-600">
      <span className="flex items-center gap-3">
        {hasLive && (
          <span className="inline-flex items-center gap-1.5 text-emerald-500 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live — auto-refreshing
          </span>
        )}
        {source === "no_api_key" && (
          <span className="text-amber-600/65">
            Schedule only — add FOOTBALL_DATA_API_KEY for live scores
          </span>
        )}
        {source === "api_forbidden" && (
          <span className="text-amber-600/65">Live scores unavailable on current API plan</span>
        )}
        {source === "api" && !hasLive && lastRefresh && (
          <span>Updated {lastRefresh.toLocaleTimeString()}</span>
        )}
      </span>
      <button
        onClick={onRefresh}
        disabled={loading}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-navy-600 hover:border-navy-500 hover:text-slate-300 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <svg
          className={`w-3 h-3 ${loading ? "animate-spin" : ""}`}
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M14 8A6 6 0 1 1 8 2" strokeLinecap="round" />
          <path d="M14 2v6h-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Refresh
      </button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LivePage() {
  const { data, loading, error, lastRefresh, refresh } = useLiveMatches();
  const [selectedDate, setSelectedDate] = useState<string>(defaultDate);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const today = todayStr();

  const liveByKey = useMemo(() => {
    const map = new Map<string, LiveMatch>();
    data?.matches.forEach((m) => {
      map.set(`${m.home_team}|${m.away_team}`, m);
      map.set(`${m.away_team}|${m.home_team}`, m);
    });
    return map;
  }, [data]);

  const dayMatches = useMemo<MergedMatch[]>(() => {
    return ALL_STATIC.filter((s) => s.date === selectedDate).map((s) => ({
      static: s,
      live: liveByKey.get(`${s.home}|${s.away}`) ?? liveByKey.get(`${s.away}|${s.home}`),
    }));
  }, [selectedDate, liveByKey]);

  const activeGroups = useMemo(
    () =>
      Array.from(new Set(ALL_STATIC.filter((m) => m.date === selectedDate).map((m) => m.group))).sort(),
    [selectedDate]
  );

  const toggleExpand = useCallback((key: string) => {
    setExpandedKey((prev) => (prev === key ? null : key));
  }, []);

  return (
    <main className="min-h-screen bg-navy-900">
      {/* ── Hero ── */}
      <section className="relative overflow-hidden border-b border-navy-700 py-12 px-6 md:px-14">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 -translate-x-1/2 top-0 w-[700px] h-[280px] rounded-full bg-emerald-500/[0.022] blur-3xl" />
          <div className="absolute left-1/2 -translate-x-1/2 top-0 w-[320px] h-[180px] rounded-full bg-fifa-blue/[0.06] blur-2xl" />
        </div>

        <div className="relative max-w-4xl mx-auto text-center space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-pitch-400 mb-4">
              FIFA World Cup 2026
            </p>
            <h1 className="font-anton text-4xl md:text-5xl text-white tracking-wide">
              MATCH CENTRE
            </h1>
          </motion.div>

          {/* Countdown — hidden when live matches are happening */}
          {!data?.has_live && <CountdownTimer data={data} />}

          {/* Live indicator */}
          {data?.has_live && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-bold tracking-wide"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Matches in progress — live scores updating
            </motion.div>
          )}
        </div>
      </section>

      {/* ── Today strip ── */}
      <TodayStrip liveByKey={liveByKey} />

      {/* ── Main content ── */}
      <div className="max-w-screen-xl mx-auto px-4 md:px-6 py-6 space-y-5">
        {/* Date nav — sticky below navbar */}
        <div
          className="sticky top-14 z-30 -mx-4 md:-mx-6 px-4 md:px-6 py-3 border-b border-navy-700"
          style={{ background: "rgba(10,12,28,0.93)", backdropFilter: "blur(12px)" }}
        >
          <DateNav
            dates={UNIQUE_DATES}
            selected={selectedDate}
            onSelect={(d) => {
              setSelectedDate(d);
              setExpandedKey(null);
            }}
            today={today}
          />
        </div>

        {/* Refresh bar */}
        {!loading && (
          <RefreshBar
            lastRefresh={lastRefresh}
            onRefresh={refresh}
            loading={loading}
            hasLive={data?.has_live ?? false}
            source={data?.source}
          />
        )}

        {/* Non-network error */}
        {error && !error.toLowerCase().includes("fetch") && (
          <div className="rounded-xl border border-red-800/50 bg-red-950/30 px-4 py-3 text-red-300 text-sm">
            Live scores unavailable: {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="rounded-xl border border-navy-700/40 bg-navy-800 overflow-hidden animate-pulse"
              >
                <div className="h-[3px] bg-navy-700" />
                <div className="h-36" />
              </div>
            ))}
          </div>
        )}

        {/* Match grid + standings */}
        {!loading && (
          <AnimatePresence mode="wait">
            <motion.div
              key={selectedDate}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18 }}
              className="space-y-8"
            >
              {dayMatches.length > 0 ? (
                <>
                  {/* Date label */}
                  <div className="flex items-center gap-3">
                    <div className="h-px flex-1 bg-navy-700/40" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-600 whitespace-nowrap">
                      {fmtDateHeading(selectedDate)}
                    </span>
                    <div className="h-px flex-1 bg-navy-700/40" />
                  </div>

                  {/* Matches */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3 gap-4">
                    {dayMatches.map((m) => {
                      const key = `${m.static.home}|${m.static.away}`;
                      return (
                        <MatchCard
                          key={key}
                          match={m}
                          expanded={expandedKey === key}
                          onToggle={() => toggleExpand(key)}
                        />
                      );
                    })}
                  </div>

                  {/* Group standings */}
                  {activeGroups.length > 0 && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <div className="h-px flex-1 bg-navy-700/30" />
                        <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-600 whitespace-nowrap">
                          Group Standings
                        </span>
                        <div className="h-px flex-1 bg-navy-700/30" />
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3 gap-4">
                        {activeGroups.map((groupId) => (
                          <GroupStandingsTable
                            key={groupId}
                            groupId={groupId}
                            liveByKey={liveByKey}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-24 gap-3 text-center">
                  <span className="text-4xl opacity-40">📅</span>
                  <p className="text-slate-500 text-sm">No matches scheduled for this date.</p>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </main>
  );
}
