"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeftIcon,
  ChevronRightIcon,
  StarIcon,
  CalendarDaysIcon,
  MapPinIcon,
  TrophyIcon,
} from "@heroicons/react/24/solid";
import { motion } from "framer-motion";
import { fetchTeam } from "@/lib/api";
import RosterSection from "@/components/RosterSection";
import { WC2026_GROUPS } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";
import type { TeamInfo } from "@/lib/types";
import { displayName } from "@/lib/utils";
import countryPaths from "@/lib/countryPaths.json";
const TEAM_CODE: Record<string, string> = {
  "United States": "USA", "Canada": "CAN", "Mexico": "MEX",
  "Germany": "GER", "France": "FRA", "Spain": "ESP", "England": "ENG",
  "Scotland": "SCO", "Portugal": "POR", "Netherlands": "NED", "Belgium": "BEL",
  "Bosnia and Herzegovina": "BIH", "Croatia": "CRO", "Czechia": "CZE",
  "Switzerland": "SUI", "Austria": "AUT", "Norway": "NOR", "Sweden": "SWE",
  "Turkey": "TUR", "Argentina": "ARG", "Brazil": "BRA", "Colombia": "COL",
  "Uruguay": "URU", "Ecuador": "ECU", "Paraguay": "PAR", "Panama": "PAN",
  "Curaçao": "CUW", "Haiti": "HAI", "Morocco": "MAR", "Senegal": "SEN",
  "Egypt": "EGY", "Ghana": "GHA", "Côte d'Ivoire": "CIV", "South Africa": "RSA",
  "DR Congo": "COD", "Tunisia": "TUN", "Algeria": "ALG", "Cape Verde Islands": "CPV",
  "Japan": "JPN", "Korea Republic": "KOR", "IR Iran": "IRN", "Australia": "AUS",
  "Saudi Arabia": "KSA", "Iraq": "IRQ", "Uzbekistan": "UZB", "Jordan": "JOR",
  "Qatar": "QAT", "New Zealand": "NZL",
};

interface Props {
  name: string;
}

const CONF_CONFIG: Record<string, {
  glowRgb: string;
  heroBorder: string;
  accentText: string;
  pill: string;
  statTop: string;
}> = {
  UEFA:     { glowRgb: "56,189,248",  heroBorder: "border-sky-500/40",     accentText: "text-sky-400",     pill: "bg-sky-400/10 border-sky-400/30 text-sky-400",              statTop: "border-t-sky-400"     },
  CONMEBOL: { glowRgb: "234,179,8",   heroBorder: "border-yellow-500/40",  accentText: "text-yellow-400",  pill: "bg-yellow-400/10 border-yellow-400/30 text-yellow-400",     statTop: "border-t-yellow-400"  },
  CONCACAF: { glowRgb: "52,211,153",  heroBorder: "border-emerald-500/40", accentText: "text-emerald-400", pill: "bg-emerald-400/10 border-emerald-400/30 text-emerald-400",  statTop: "border-t-emerald-400" },
  CAF:      { glowRgb: "251,146,60",  heroBorder: "border-orange-500/40",  accentText: "text-orange-400",  pill: "bg-orange-400/10 border-orange-400/30 text-orange-400",     statTop: "border-t-orange-400"  },
  AFC:      { glowRgb: "248,113,113", heroBorder: "border-red-500/40",     accentText: "text-red-400",     pill: "bg-red-400/10 border-red-400/30 text-red-400",              statTop: "border-t-red-400"     },
  OFC:      { glowRgb: "192,132,252", heroBorder: "border-purple-500/40",  accentText: "text-purple-400",  pill: "bg-purple-400/10 border-purple-400/30 text-purple-400",     statTop: "border-t-purple-400"  },
  _default: { glowRgb: "100,116,139", heroBorder: "border-slate-500/40",   accentText: "text-slate-400",   pill: "bg-slate-400/10 border-slate-400/30 text-slate-400",        statTop: "border-t-slate-400"   },
};

const CONF_TEAM_COUNTS: Record<string, number> = {
  UEFA: 16, CONMEBOL: 6, CONCACAF: 6, CAF: 9, AFC: 8, OFC: 1,
};

const HOST_TEAMS = new Set(["United States", "Canada", "Mexico"]);


function formatDateShort(iso: string) {
  return new Date(iso + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function useCountUp(target: number | null, active: boolean) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!active || target == null) return;
    if (target < 10) { setVal(target); return; }
    const duration = Math.min(1500, 500 + target * 30);
    const start = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setVal(Math.round(eased * target));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, active]);
  return val;
}

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1, delayChildren: 0.05 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

function SkeletonPulse({ className }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded-2xl bg-navy-700/60 border border-navy-600/50 ${className ?? ""}`} />
  );
}

export default function TeamProfilePage({ name }: Props) {
  const router = useRouter();
  const [team, setTeam] = useState<TeamInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rankReady, setRankReady] = useState(false);

  const teamCode = TEAM_CODE[name] ?? null;
  const countryPath = (countryPaths as Record<string, { d: string; viewBox: string }>)[name] ?? null;

  useEffect(() => {
    setLoading(true);
    setError(null);
    setRankReady(false);
    fetchTeam(name)
      .then(setTeam)
      .catch((e) => setError(e.message ?? "Failed to load team"))
      .finally(() => setLoading(false));
  }, [name]);

  useEffect(() => {
    if (team) {
      const t = setTimeout(() => setRankReady(true), 700);
      return () => clearTimeout(t);
    }
  }, [team]);

  const rankDisplay = useCountUp(team?.fifa_rank ?? null, rankReady);

  const wcGroup = WC2026_GROUPS.find((g) => g.teams.includes(name)) ?? null;
  const groupFixtures = wcGroup?.matches.filter((m) => m.home === name || m.away === name) ?? [];
  const teammates = wcGroup?.teams.filter((t) => t !== name) ?? [];

  const conf = CONF_CONFIG[team?.confederation ?? "_default"] ?? CONF_CONFIG["_default"];
  const shortName = displayName(name);

  return (
    <main className="min-h-screen bg-navy-900 relative overflow-x-hidden">
      {/* Atmospheric glows */}
      {team && (
        <>
          <div
            className="pointer-events-none fixed top-0 left-1/3 w-[700px] h-[500px] rounded-full blur-[140px] -translate-y-1/2 -translate-x-1/4"
            style={{ background: `rgba(${conf.glowRgb}, 0.07)` }}
          />
          <div
            className="pointer-events-none fixed bottom-0 right-0 w-[500px] h-[400px] rounded-full blur-[120px] translate-y-1/3"
            style={{ background: `rgba(${conf.glowRgb}, 0.04)` }}
          />
        </>
      )}

      <div className="relative max-w-4xl mx-auto px-4 py-10 flex flex-col gap-6">
        {/* Back nav */}
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="flex items-center gap-3"
        >
          <button
            onClick={() => router.back()}
            className="p-1.5 rounded-lg bg-navy-800 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue transition-colors cursor-pointer"
            aria-label="Go back"
          >
            <ArrowLeftIcon className="h-4 w-4" />
          </button>
          <Link href="/teams" className="text-sm text-slate-500 hover:text-slate-300 transition-colors">
            All Teams
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-sm text-slate-300 font-medium truncate">{name}</span>
        </motion.div>

        {/* Loading skeleton */}
        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
            <SkeletonPulse className="h-44" />
            <div className="grid grid-cols-3 gap-3">
              {[...Array(3)].map((_, i) => <SkeletonPulse key={i} className="h-28" />)}
            </div>
            <SkeletonPulse className="h-40" />
            <SkeletonPulse className="h-52" />
            <SkeletonPulse className="h-28" />
          </motion.div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
            {error === "Failed to fetch"
              ? "Cannot connect to backend — make sure the FastAPI server is running on port 8000."
              : error}
          </div>
        )}

        {/* Main content */}
        {!loading && !error && team && (
          <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="flex flex-col gap-6">

            {/* ── Hero card ── */}
            <motion.div variants={fadeUp}>
              <div
                className={`relative overflow-hidden rounded-2xl border ${conf.heroBorder} bg-navy-800`}
                style={{
                  boxShadow: `0 0 50px rgba(${conf.glowRgb}, 0.14), 0 0 100px rgba(${conf.glowRgb}, 0.06)`,
                }}
              >
                {/* ── Geo silhouette + country code watermark ── */}
                {(teamCode || countryPath) && (
                  <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    {/* Layer 1: country map silhouette — center-right zone */}
                    {countryPath && (
                      <svg
                        aria-hidden
                        viewBox={countryPath.viewBox}
                        className="absolute top-1/2 -translate-y-1/2 h-[115%] w-auto"
                        style={{ right: "26%", opacity: 0.20 }}
                        preserveAspectRatio="xMidYMid meet"
                      >
                        <path d={countryPath.d} fill={`rgba(${conf.glowRgb}, 1)`} />
                      </svg>
                    )}
                    {/* Layer 2: country code text — far-right edge */}
                    {teamCode && (
                      <div className="absolute top-1/2 -translate-y-1/2 right-5 flex items-center">
                        <span
                          aria-hidden
                          className="font-anton select-none leading-none tracking-tight"
                          style={{
                            fontSize: "8.5rem",
                            color: `rgba(${conf.glowRgb}, 1)`,
                            opacity: 0.28,
                            writingMode: "vertical-rl",
                            textOrientation: "mixed",
                            transform: "rotate(180deg)",
                          }}
                        >
                          {teamCode}
                        </span>
                      </div>
                    )}
                    {/* Layer 3: gradient mask — solid left, transparent right */}
                    <div
                      className="absolute inset-0"
                      style={{
                        background:
                          "linear-gradient(to right, #0e1020 22%, rgba(14,16,32,0.80) 44%, rgba(14,16,32,0.10) 72%, transparent 100%)",
                      }}
                    />
                  </div>
                )}

                {/* Radial glow overlay */}
                <div
                  className="absolute inset-0"
                  style={{
                    background: `radial-gradient(ellipse at 10% 50%, rgba(${conf.glowRgb}, 0.13) 0%, transparent 60%)`,
                  }}
                />
                {/* Top edge highlight */}
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                {/* Gloss sheen */}
                <div className="absolute inset-0 bg-gradient-to-b from-white/[0.025] to-transparent" />

                <div className="relative p-7 sm:p-10 flex flex-col sm:flex-row items-start sm:items-center gap-6">
                  {/* Flag */}
                  <motion.div
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
                    className="flex-shrink-0"
                  >
                    <FlagIcon
                      team={name}
                      className="w-28 h-20 sm:w-32 sm:h-[88px] rounded-xl shadow-2xl"
                    />
                  </motion.div>

                  <div className="flex flex-col gap-3 min-w-0 flex-1">
                    {/* WC 2026 eyebrow */}
                    <div className="flex items-center gap-2">
                      <TrophyIcon className="h-3.5 w-3.5 text-yellow-500/60" />
                      <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-[0.2em]">
                        FIFA World Cup 2026
                      </span>
                    </div>

                    {/* Team name */}
                    <motion.h1
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5, ease: "easeOut", delay: 0.2 }}
                      className="font-anton text-4xl sm:text-5xl text-white leading-none tracking-wide"
                    >
                      {name}
                    </motion.h1>

                    {/* Badges */}
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.45, ease: "easeOut", delay: 0.3 }}
                      className="flex flex-wrap items-center gap-2"
                    >
                      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${conf.pill}`}>
                        {team.confederation}
                      </span>
                      {wcGroup && (
                        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full border border-navy-500 text-slate-400 bg-navy-700">
                          Group {wcGroup.id}
                        </span>
                      )}
                      {HOST_TEAMS.has(name) && (
                        <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-yellow-500/40 text-yellow-400 bg-yellow-400/10">
                          <StarIcon className="h-3 w-3" />
                          Host Nation
                        </span>
                      )}
                    </motion.div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* ── Stats strip ── */}
            <motion.div variants={fadeUp} className="grid grid-cols-3 gap-3">
              {/* Confederation */}
              <div className={`relative overflow-hidden bg-navy-800 border border-navy-600 border-t-2 ${conf.statTop} rounded-xl p-4 flex flex-col gap-1`}>
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Confederation</span>
                <span className={`text-lg sm:text-xl font-bold ${conf.accentText} truncate`}>
                  {team.confederation}
                </span>
                <span className="text-xs text-slate-500">
                  {CONF_TEAM_COUNTS[team.confederation] ?? "—"} teams
                </span>
              </div>

              {/* FIFA Rank */}
              <div className="relative overflow-hidden bg-navy-800 border border-navy-600 border-t-2 border-t-yellow-400 rounded-xl p-4 flex flex-col gap-1">
                <div
                  className="absolute inset-0 opacity-[0.04]"
                  style={{ background: "radial-gradient(ellipse at 50% 0%, rgba(234,179,8,1), transparent 70%)" }}
                />
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">FIFA Rank</span>
                <span
                  className="text-2xl sm:text-3xl font-bold text-yellow-400 font-jb"
                  style={{ textShadow: rankReady ? "0 0 20px rgba(234,179,8,0.55)" : "none" }}
                >
                  {team.fifa_rank != null ? `#${rankDisplay}` : "—"}
                </span>
                <span className="text-xs text-slate-500">2025 ranking</span>
              </div>

              {/* WC Group */}
              <div className="relative overflow-hidden bg-navy-800 border border-navy-600 border-t-2 border-t-fifa-blue rounded-xl p-4 flex flex-col gap-1">
                <div className="absolute inset-x-0 top-0 h-10 bg-gradient-to-b from-fifa-blue/5 to-transparent" />
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">WC Group</span>
                <span className="text-2xl sm:text-3xl font-bold text-fifa-blue-light font-jb">
                  {wcGroup ? wcGroup.id : "—"}
                </span>
                <span className="text-[10px] text-slate-500 truncate leading-tight">
                  {teammates.length > 0
                    ? teammates.map((t) => displayName(t)).join(" · ")
                    : "Group TBD"}
                </span>
              </div>
            </motion.div>

            {/* ── Group Teammates ── */}
            {teammates.length > 0 && (
              <motion.div variants={fadeUp} className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-4">
                <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Group {wcGroup?.id} · Other Teams
                </h2>
                <div className={`grid gap-3 ${teammates.length === 3 ? "grid-cols-3" : "grid-cols-2 sm:grid-cols-3"}`}>
                  {teammates.map((tm, i) => (
                    <motion.div
                      key={tm}
                      initial={{ opacity: 0, scale: 0.92 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.4, delay: 0.12 + i * 0.07, ease: "easeOut" }}
                    >
                      <Link
                        href={`/teams/${encodeURIComponent(tm)}`}
                        className="flex flex-col items-center gap-2.5 p-4 rounded-xl bg-navy-700 border border-navy-600 hover:border-slate-500 hover:bg-navy-600 hover:-translate-y-0.5 transition-all group cursor-pointer"
                      >
                        <FlagIcon team={tm} className="w-16 h-11 rounded-lg shadow-md" />
                        <span className="text-xs font-semibold text-slate-300 text-center leading-tight group-hover:text-white transition-colors">
                          {displayName(tm)}
                        </span>
                      </Link>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* ── Group Stage Fixtures ── */}
            {groupFixtures.length > 0 && (
              <motion.div variants={fadeUp} className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-4">
                <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Group Stage Fixtures
                </h2>
                <div className="flex flex-col gap-3">
                  {groupFixtures.map((match, idx) => {
                    const params = new URLSearchParams({
                      home: match.home,
                      away: match.away,
                      date: match.date,
                      stage: "Group Stage",
                    });
                    return (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: -12 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.4, delay: 0.1 + idx * 0.09 }}
                        className="rounded-xl border border-navy-600 overflow-hidden"
                      >
                        {/* Matchday header bar */}
                        <div className="px-4 py-1.5 bg-navy-700 border-b border-navy-600 flex items-center justify-between">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.15em]">
                            MD {idx + 1}
                          </span>
                          <div className="flex items-center gap-3 text-[10px] text-slate-500">
                            <span className="flex items-center gap-1">
                              <CalendarDaysIcon className="h-3 w-3" />
                              {formatDateShort(match.date)}
                            </span>
                            <span className="hidden sm:flex items-center gap-1">
                              <MapPinIcon className="h-3 w-3" />
                              <span className="truncate max-w-[130px]">{match.venue}</span>
                            </span>
                          </div>
                        </div>

                        {/* Teams row */}
                        <div className="px-4 py-3 bg-navy-700/50 flex items-center gap-2">
                          {/* Home team */}
                          <div className="flex-1 flex items-center gap-2.5 min-w-0">
                            <FlagIcon team={match.home} className="w-9 h-6 rounded-md flex-shrink-0" />
                            <span
                              className={`text-sm font-semibold truncate ${
                                match.home === name ? "text-white" : "text-slate-400"
                              }`}
                            >
                              {displayName(match.home)}
                            </span>
                          </div>

                          <span className="flex-shrink-0 text-xs font-bold text-slate-600 tracking-widest px-1">
                            VS
                          </span>

                          {/* Away team */}
                          <div className="flex-1 flex items-center justify-end gap-2.5 min-w-0">
                            <span
                              className={`text-sm font-semibold truncate text-right ${
                                match.away === name ? "text-white" : "text-slate-400"
                              }`}
                            >
                              {displayName(match.away)}
                            </span>
                            <FlagIcon team={match.away} className="w-9 h-6 rounded-md flex-shrink-0" />
                          </div>

                          {/* Predict link */}
                          <Link
                            href={`/predict?${params.toString()}`}
                            className="ml-2 flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-fifa-blue/10 border border-fifa-blue/30 text-fifa-blue-light text-xs font-semibold hover:bg-fifa-blue/20 hover:border-fifa-blue/60 transition-all cursor-pointer"
                          >
                            Predict
                            <ChevronRightIcon className="h-3 w-3" />
                          </Link>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            )}

            {/* ── Squad Roster ── */}
            <RosterSection team={name} />

            {/* ── Predict CTA ── */}
            <motion.div
              variants={fadeUp}
              className="rounded-2xl border border-navy-600 bg-navy-800 p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div>
                <h2 className="text-base font-bold text-white mb-1">Predict a Match</h2>
                <p className="text-slate-400 text-sm max-w-sm">
                  Run AI-powered head-to-head predictions for {shortName} against any WC 2026 team.
                </p>
              </div>
              <Link
                href={`/predict?home=${encodeURIComponent(name)}`}
                className="flex-shrink-0 self-start sm:self-auto flex items-center gap-2 px-6 py-3 rounded-xl text-white text-sm font-bold transition-all cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
                style={{
                  background: `linear-gradient(135deg, rgba(${conf.glowRgb}, 0.85) 0%, rgba(${conf.glowRgb}, 0.55) 100%)`,
                  boxShadow: `0 4px 20px rgba(${conf.glowRgb}, 0.4), 0 0 0 1px rgba(${conf.glowRgb}, 0.2)`,
                }}
              >
                Predict {shortName} vs …
                <ChevronRightIcon className="h-4 w-4" />
              </Link>
            </motion.div>

          </motion.div>
        )}

        {/* Not found */}
        {!loading && !error && !team && (
          <div className="bg-navy-800 rounded-2xl border border-navy-600 p-8 text-center flex flex-col gap-3">
            <span className="text-slate-300 font-semibold">Team not found</span>
            <p className="text-slate-500 text-sm">
              &ldquo;{name}&rdquo; — check spelling or browse all teams below.
            </p>
            <Link href="/teams" className="self-center text-sm text-fifa-blue-light hover:underline mt-1">
              Browse all WC 2026 teams →
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
