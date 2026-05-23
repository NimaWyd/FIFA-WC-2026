"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { MagnifyingGlassIcon, StarIcon, XMarkIcon } from "@heroicons/react/24/solid";
import { motion } from "framer-motion";
import { WC2026_TEAMS } from "@/lib/wc2026Teams";
import { WC2026_GROUPS } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";
import { displayName } from "@/lib/utils";

const HOST_TEAMS = new Set(["United States", "Canada", "Mexico"]);

const TEAM_CONF: Record<string, string> = {
  "United States": "CONCACAF", "Canada": "CONCACAF", "Mexico": "CONCACAF",
  "Germany": "UEFA", "France": "UEFA", "Spain": "UEFA", "England": "UEFA",
  "Portugal": "UEFA", "Netherlands": "UEFA", "Belgium": "UEFA",
  "Bosnia and Herzegovina": "UEFA", "Croatia": "UEFA", "Czechia": "UEFA",
  "Switzerland": "UEFA", "Austria": "UEFA", "Norway": "UEFA",
  "Sweden": "UEFA", "Turkey": "UEFA", "Scotland": "UEFA",
  "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Colombia": "CONMEBOL",
  "Uruguay": "CONMEBOL", "Ecuador": "CONMEBOL", "Paraguay": "CONMEBOL",
  "Panama": "CONCACAF", "Curaçao": "CONCACAF", "Haiti": "CONCACAF",
  "Morocco": "CAF", "Senegal": "CAF", "Egypt": "CAF", "Ghana": "CAF",
  "Côte d'Ivoire": "CAF", "South Africa": "CAF", "DR Congo": "CAF",
  "Tunisia": "CAF", "Algeria": "CAF", "Cape Verde Islands": "CAF",
  "Japan": "AFC", "Korea Republic": "AFC", "IR Iran": "AFC",
  "Australia": "AFC", "Saudi Arabia": "AFC", "Iraq": "AFC",
  "Uzbekistan": "AFC", "Jordan": "AFC", "Qatar": "AFC",
  "New Zealand": "OFC",
};

const CONF_STYLES: Record<string, {
  leftBorder: string;
  activeBg: string; activeText: string; activeBorder: string;
  pillBg: string; pillText: string; pillBorder: string;
  hoverRing: string;
}> = {
  UEFA:     { leftBorder: "border-l-sky-400",     activeBg: "bg-sky-500/15",     activeText: "text-sky-300",     activeBorder: "border-sky-500/40",     pillBg: "bg-sky-500/10",     pillText: "text-sky-400",     pillBorder: "border-sky-400/30",     hoverRing: "hover:ring-sky-400/30" },
  CONMEBOL: { leftBorder: "border-l-yellow-400",  activeBg: "bg-yellow-500/15",  activeText: "text-yellow-300",  activeBorder: "border-yellow-500/40",  pillBg: "bg-yellow-500/10",  pillText: "text-yellow-400",  pillBorder: "border-yellow-400/30",  hoverRing: "hover:ring-yellow-400/30" },
  CONCACAF: { leftBorder: "border-l-emerald-400", activeBg: "bg-emerald-500/15", activeText: "text-emerald-300", activeBorder: "border-emerald-500/40", pillBg: "bg-emerald-500/10", pillText: "text-emerald-400", pillBorder: "border-emerald-400/30", hoverRing: "hover:ring-emerald-400/30" },
  CAF:      { leftBorder: "border-l-orange-400",  activeBg: "bg-orange-500/15",  activeText: "text-orange-300",  activeBorder: "border-orange-500/40",  pillBg: "bg-orange-500/10",  pillText: "text-orange-400",  pillBorder: "border-orange-400/30",  hoverRing: "hover:ring-orange-400/30" },
  AFC:      { leftBorder: "border-l-red-400",     activeBg: "bg-red-500/15",     activeText: "text-red-300",     activeBorder: "border-red-500/40",     pillBg: "bg-red-500/10",     pillText: "text-red-400",     pillBorder: "border-red-400/30",     hoverRing: "hover:ring-red-400/30" },
  OFC:      { leftBorder: "border-l-purple-400",  activeBg: "bg-purple-500/15",  activeText: "text-purple-300",  activeBorder: "border-purple-500/40",  pillBg: "bg-purple-500/10",  pillText: "text-purple-400",  pillBorder: "border-purple-400/30",  hoverRing: "hover:ring-purple-400/30" },
};

const CONFEDERATIONS = ["All", "UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"] as const;
type Confederation = (typeof CONFEDERATIONS)[number];

const CONF_TEAM_COUNTS: Record<string, number> = {
  UEFA: 16, CONMEBOL: 6, CONCACAF: 6, CAF: 10, AFC: 9, OFC: 1,
};

const STATS = [
  { value: "48", label: "Teams" },
  { value: "12", label: "Groups" },
  { value: "6",  label: "Confeds" },
  { value: "3",  label: "Hosts" },
];

function getGroup(team: string): string | null {
  return WC2026_GROUPS.find((g) => g.teams.includes(team))?.id ?? null;
}

const TEAMS_ARRAY = Array.from(WC2026_TEAMS);

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05, delayChildren: 0.02 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" as const } },
};

function TeamCard({ team }: { team: string }) {
  const conf = TEAM_CONF[team];
  const cs = conf ? CONF_STYLES[conf] : null;
  const group = getGroup(team);
  const isHost = HOST_TEAMS.has(team);
  const teamDisplayName = displayName(team);

  return (
    <motion.div variants={cardVariants}>
      <Link
        href={`/teams/${encodeURIComponent(team)}`}
        className={[
          "group relative flex flex-col items-center gap-3 p-4",
          "bg-navy-800 border border-navy-600 rounded-xl overflow-hidden cursor-pointer",
          cs ? `border-l-4 ${cs.leftBorder}` : "",
          isHost ? "ring-1 ring-yellow-400/25" : "",
          "hover:-translate-y-1 hover:shadow-[0_12px_36px_rgba(0,0,0,0.65)]",
          cs ? `hover:ring-2 ${cs.hoverRing}` : "",
          "hover:border-navy-500 transition-all duration-200",
        ].join(" ")}
      >
        {/* Subtle inner top-gloss */}
        <div className="absolute inset-0 bg-gradient-to-b from-white/[0.025] to-transparent pointer-events-none" />

        {isHost && (
          <span className="absolute top-2 right-2 z-10 flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-yellow-400/10 border border-yellow-400/25 text-yellow-400">
            <StarIcon className="w-2.5 h-2.5" />
            <span className="text-[9px] font-bold tracking-wide">HOST</span>
          </span>
        )}

        <FlagIcon team={team} className="w-16 h-12 rounded-md shadow-md flex-shrink-0 mt-1 relative z-10" />

        <div className="min-h-[2.5rem] flex items-center justify-center w-full relative z-10">
          <span className="text-sm font-bold text-white text-center leading-tight group-hover:text-fifa-blue-light transition-colors line-clamp-2">
            {teamDisplayName}
          </span>
        </div>

        <div className="flex items-center gap-1 flex-wrap justify-center relative z-10">
          {group && (
            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-navy-700 border border-navy-600 text-slate-500 tabular-nums">
              GRP {group}
            </span>
          )}
          {conf && cs && (
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${cs.pillBg} ${cs.pillText} ${cs.pillBorder}`}>
              {conf}
            </span>
          )}
        </div>
      </Link>
    </motion.div>
  );
}

export default function TeamsIndexPage() {
  const [search, setSearch] = useState("");
  const [confFilter, setConfFilter] = useState<Confederation>("All");

  const isFiltering = search.trim() !== "" || confFilter !== "All";

  const filtered = useMemo(() => {
    return TEAMS_ARRAY.filter((t) => {
      const matchesSearch = t.toLowerCase().includes(search.toLowerCase());
      const matchesConf = confFilter === "All" || TEAM_CONF[t] === confFilter;
      return matchesSearch && matchesConf;
    }).sort((a, b) => {
      const ga = getGroup(a) ?? "Z";
      const gb = getGroup(b) ?? "Z";
      if (ga !== gb) return ga.localeCompare(gb);
      return a.localeCompare(b);
    });
  }, [search, confFilter]);

  return (
    <main className="min-h-screen bg-navy-900 relative overflow-hidden">

      {/* Atmospheric background glows — stadium spotlight feel */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute -top-56 left-1/4 w-[750px] h-[750px] rounded-full bg-fifa-blue/[0.07] blur-[140px]" />
        <div className="absolute top-[55%] -right-[18%] w-[550px] h-[550px] rounded-full bg-gold-500/[0.055] blur-[120px]" />
        <div className="absolute -bottom-32 -left-[8%] w-[480px] h-[480px] rounded-full bg-pitch-400/[0.04] blur-[120px]" />
      </div>

      <div className="relative max-w-5xl mx-auto px-4 py-10 flex flex-col gap-8">

        {/* ── Header ── */}
        <motion.div
          initial={{ opacity: 0, y: -14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col gap-3"
        >
          {/* Badge + date + gradient rule */}
          <div className="flex items-center gap-3">
            <span className="shrink-0 text-[10px] font-bold tracking-[0.15em] uppercase px-2.5 py-1 rounded border border-gold-500/40 bg-gold-500/10 text-gold-500">
              FIFA World Cup
            </span>
            <span className="shrink-0 text-[11px] text-slate-600 font-medium">June – July 2026</span>
            <div className="flex-1 h-px bg-gradient-to-r from-gold-500/25 to-transparent" />
          </div>

          {/* Title row + stats */}
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-5">
            <div>
              <div className="flex items-baseline gap-3">
                <h1 className="font-anton text-5xl sm:text-6xl text-white tracking-wide leading-none">
                  WC 2026
                </h1>
                <span className="font-anton text-2xl sm:text-3xl text-fifa-blue-light tracking-wider leading-none">
                  TEAMS
                </span>
              </div>
              <p className="text-slate-500 text-sm mt-2">
                All {WC2026_TEAMS.size} qualified nations · click a team to view its profile
              </p>
            </div>

            {/* Gold stats strip */}
            <div className="flex items-center divide-x divide-navy-600 shrink-0">
              {STATS.map(({ value, label }) => (
                <div key={label} className="text-center px-4 first:pl-0 last:pr-0">
                  <div
                    className="font-anton text-2xl sm:text-3xl text-gold-500 leading-none"
                    style={{ textShadow: "0 0 24px rgba(245,200,66,0.55)" }}
                  >
                    {value}
                  </div>
                  <div className="text-[10px] text-slate-600 uppercase tracking-widest mt-0.5">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Gradient divider */}
        <div className="h-px bg-gradient-to-r from-transparent via-navy-600 to-transparent" />

        {/* ── Search & Filter ── */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="flex flex-col gap-4"
        >
          <div className="relative max-w-sm">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
            <input
              type="text"
              placeholder="Search teams…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg bg-navy-800 border border-navy-600 text-white pl-9 pr-9 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-fifa-blue focus:border-transparent placeholder:text-slate-500 transition-all"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
                aria-label="Clear search"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Confederation filter pills */}
          <div className="flex flex-wrap gap-2">
            {CONFEDERATIONS.map((conf) => {
              const isActive = confFilter === conf;
              const cs = conf !== "All" ? CONF_STYLES[conf] : null;
              const count = conf !== "All" ? CONF_TEAM_COUNTS[conf] : null;
              return (
                <button
                  key={conf}
                  onClick={() => setConfFilter(conf)}
                  className={[
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-200 cursor-pointer",
                    isActive
                      ? conf === "All"
                        ? "bg-fifa-blue border-fifa-blue/80 text-white shadow-[0_0_16px_rgba(26,63,255,0.45)]"
                        : `${cs!.activeBg} ${cs!.activeText} ${cs!.activeBorder}`
                      : "bg-navy-800 border-navy-600 text-slate-500 hover:border-navy-500 hover:text-slate-300",
                  ].join(" ")}
                >
                  {conf}
                  {count && (
                    <span className={`text-[10px] tabular-nums ${isActive ? "opacity-70" : "opacity-40"}`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </motion.div>

        {/* ── Content ── */}
        {filtered.length === 0 ? (
          <div className="text-slate-500 text-sm py-16 text-center">
            No teams match &ldquo;{search}&rdquo;
          </div>
        ) : isFiltering ? (
          /* Flat grid when filtering */
          <motion.div
            key="flat"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3"
          >
            {filtered.map((team) => (
              <TeamCard key={team} team={team} />
            ))}
          </motion.div>
        ) : (
          /* Default: grouped by tournament group */
          <motion.div
            key="grouped"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.25 }}
            className="flex flex-col gap-10"
          >
            {WC2026_GROUPS.map((group, gi) => (
              <motion.div
                key={group.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: gi * 0.055 }}
                className="flex flex-col gap-3 relative"
              >
                {/* Group header — "GROUP" small + large faint letter as one typographic unit */}
                <div className="flex items-center gap-3">
                  <div className="flex items-baseline gap-2 shrink-0">
                    <span className="font-anton text-sm text-slate-500 tracking-[0.2em] uppercase leading-none">
                      GROUP
                    </span>
                    <span className="font-anton text-5xl text-white leading-none tracking-wider" style={{ opacity: 0.18 }}>
                      {group.id}
                    </span>
                  </div>
                  <div className="flex-1 h-px bg-gradient-to-r from-gold-500/35 to-transparent" />
                  <span className="text-[11px] text-slate-600 font-medium tabular-nums shrink-0">
                    4 teams
                  </span>
                </div>

                {/* Team cards */}
                <motion.div
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                  className="grid grid-cols-2 sm:grid-cols-4 gap-3"
                >
                  {group.teams.map((team) => (
                    <TeamCard key={team} team={team} />
                  ))}
                </motion.div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </main>
  );
}
