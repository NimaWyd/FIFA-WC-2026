"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeftIcon, ChevronRightIcon } from "@heroicons/react/24/solid";
import { motion } from "framer-motion";
import { fetchTeam } from "@/lib/api";
import { WC2026_GROUPS } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";
import TeamStatCard from "@/components/TeamStatCard";
import type { TeamInfo } from "@/lib/types";

interface Props {
  name: string;
}

const CONF_COLORS: Record<string, string> = {
  UEFA: "text-sky-400 bg-sky-400/10 border-sky-400/30",
  CONMEBOL: "text-gold-500 bg-gold-500/10 border-gold-500/30",
  CONCACAF: "text-pitch-400 bg-pitch-400/10 border-pitch-400/30",
  CAF: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  AFC: "text-red-400 bg-red-400/10 border-red-400/30",
  OFC: "text-purple-400 bg-purple-400/10 border-purple-400/30",
};

const HOST_TEAMS = new Set(["United States", "Canada", "Mexico"]);

function formatDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, delay: i * 0.08, ease: "easeOut" as const },
  }),
};

export default function TeamProfilePage({ name }: Props) {
  const router = useRouter();
  const [team, setTeam] = useState<TeamInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchTeam(name)
      .then(setTeam)
      .catch((e) => setError(e.message ?? "Failed to load team"))
      .finally(() => setLoading(false));
  }, [name]);

  const wcGroup = WC2026_GROUPS.find((g) => g.teams.includes(name)) ?? null;
  const groupFixtures = wcGroup?.matches.filter(
    (m) => m.home === name || m.away === name
  ) ?? [];

  const confStyle = team ? (CONF_COLORS[team.confederation] ?? "text-slate-400 bg-slate-400/10 border-slate-400/30") : "";

  return (
    <main className="min-h-screen bg-navy-900">
      <div className="max-w-4xl mx-auto px-4 py-10 flex flex-col gap-6">
        {/* Back nav */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="p-1.5 rounded-lg bg-navy-800 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue transition-colors"
            aria-label="Go back"
          >
            <ArrowLeftIcon className="h-4 w-4" />
          </button>
          <Link href="/teams" className="text-sm text-slate-500 hover:text-slate-300 transition-colors">
            All Teams
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-sm text-slate-300 font-medium">{name}</span>
        </div>

        {loading && (
          <div className="text-slate-400 text-sm py-16 text-center">Loading team data…</div>
        )}

        {error && (
          <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
            {error === "Failed to fetch"
              ? "Cannot connect to backend — make sure the FastAPI server is running on port 8000."
              : error}
          </div>
        )}

        {!loading && !error && team && (
          <>
            {/* ── Team header ── */}
            <motion.div
              custom={0} initial="hidden" animate="visible" variants={cardVariants}
              className="bg-navy-800 rounded-2xl border border-navy-600 p-6"
            >
              <div className="flex items-center gap-5">
                <FlagIcon team={name} className="w-20 h-14 rounded-lg flex-shrink-0" />
                <div className="flex flex-col gap-2 min-w-0">
                  <h1 className="text-2xl font-bold text-white leading-tight">{name}</h1>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${confStyle}`}>
                      {team.confederation}
                    </span>
                    {wcGroup && (
                      <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full border border-navy-500 text-slate-400 bg-navy-700">
                        Group {wcGroup.id}
                      </span>
                    )}
                    {HOST_TEAMS.has(name) && (
                      <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full border border-gold-500/40 text-gold-500 bg-gold-500/10">
                        Host
                      </span>
                    )}
                  </div>
                  {team.fifa_rank && (
                    <span className="text-sm text-slate-400">
                      #{team.fifa_rank} · FIFA World Ranking
                    </span>
                  )}
                </div>
              </div>
            </motion.div>

            {/* ── Key stats strip ── */}
            <motion.div
              custom={1} initial="hidden" animate="visible" variants={cardVariants}
              className="grid grid-cols-2 sm:grid-cols-3 gap-3"
            >
              <TeamStatCard
                label="FIFA Rank"
                value={team.fifa_rank ? `#${team.fifa_rank}` : null}
                sub="2025 FIFA World Ranking"
              />
              <TeamStatCard
                label="Confederation"
                value={team.confederation}
              />
              <TeamStatCard
                label="WC 2026 Group"
                value={wcGroup ? `Group ${wcGroup.id}` : null}
                sub={wcGroup?.teams.filter((t) => t !== name).join(", ")}
              />
            </motion.div>

            {/* ── Group fixtures ── */}
            {groupFixtures.length > 0 && (
              <motion.div
                custom={2} initial="hidden" animate="visible" variants={cardVariants}
                className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-4"
              >
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                  Group Stage Fixtures
                </h2>
                <div className="flex flex-col gap-2">
                  {groupFixtures.map((match, idx) => {
                    const opponent = match.home === name ? match.away : match.home;
                    const isHome = match.home === name;
                    const params = new URLSearchParams({
                      home: match.home,
                      away: match.away,
                      date: match.date,
                      stage: "Group Stage",
                    });
                    return (
                      <div
                        key={idx}
                        className="flex items-center gap-3 p-3 rounded-xl bg-navy-700 border border-navy-600"
                      >
                        <div className="hidden sm:flex flex-col w-20 flex-shrink-0">
                          <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                            MD {idx + 1}
                          </span>
                          <span className="text-xs text-slate-400">{formatDate(match.date)}</span>
                          <span className="text-[10px] text-slate-600 truncate">{match.venue}</span>
                        </div>
                        <div className="flex-1 flex items-center gap-2 min-w-0">
                          <FlagIcon team={opponent} className="w-7 h-5 rounded-sm flex-shrink-0" />
                          <div className="min-w-0">
                            <span className="text-sm font-semibold text-white truncate block">
                              {isHome ? "vs" : "@"} {opponent === "United States" ? "USA" : opponent}
                            </span>
                            <span className="sm:hidden text-[10px] text-slate-500">
                              {formatDate(match.date)} · {match.venue}
                            </span>
                          </div>
                        </div>
                        <Link
                          href={`/predict?${params.toString()}`}
                          className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-fifa-blue/10 border border-fifa-blue/30 text-fifa-blue-light text-xs font-semibold hover:bg-fifa-blue/20 hover:border-fifa-blue/60 transition-all"
                        >
                          Predict
                          <ChevronRightIcon className="h-3 w-3" />
                        </Link>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}

            {/* ── Predict CTA ── */}
            <motion.div
              custom={3} initial="hidden" animate="visible" variants={cardVariants}
              className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-3"
            >
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                Predict a Match
              </h2>
              <p className="text-slate-400 text-sm">
                See how {name} performs against any other team.
              </p>
              <Link
                href={`/predict?home=${encodeURIComponent(name)}`}
                className="self-start flex items-center gap-2 px-5 py-2.5 rounded-xl bg-fifa-blue text-white text-sm font-bold hover:bg-fifa-blue/90 shadow-[0_2px_12px_rgba(26,63,255,0.4)] transition-colors"
              >
                Predict {name === "United States" ? "USA" : name} vs …
                <ChevronRightIcon className="h-4 w-4" />
              </Link>
            </motion.div>
          </>
        )}

        {/* Not found */}
        {!loading && !error && !team && (
          <div className="bg-navy-800 rounded-2xl border border-navy-600 p-8 text-center flex flex-col gap-3">
            <span className="text-slate-300 font-semibold">Team not found</span>
            <p className="text-slate-500 text-sm">
              &ldquo;{name}&rdquo; — check spelling or browse all teams below.
            </p>
            <Link
              href="/teams"
              className="self-center text-sm text-fifa-blue-light hover:underline mt-1"
            >
              Browse all WC 2026 teams →
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
