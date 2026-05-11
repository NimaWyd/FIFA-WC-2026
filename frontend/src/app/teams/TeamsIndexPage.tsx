"use client";

import { useState } from "react";
import Link from "next/link";
import { MagnifyingGlassIcon } from "@heroicons/react/24/solid";
import { WC2026_TEAMS } from "@/lib/wc2026Teams";
import { WC2026_GROUPS } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";

const HOST_TEAMS = new Set(["United States", "Canada", "Mexico"]);

function getGroup(team: string): string | null {
  return WC2026_GROUPS.find((g) => g.teams.includes(team))?.id ?? null;
}

const TEAMS_ARRAY = Array.from(WC2026_TEAMS);

export default function TeamsIndexPage() {
  const [search, setSearch] = useState("");

  const filtered = TEAMS_ARRAY.filter((t) =>
    t.toLowerCase().includes(search.toLowerCase())
  ).sort((a, b) => {
    const ga = getGroup(a) ?? "Z";
    const gb = getGroup(b) ?? "Z";
    if (ga !== gb) return ga.localeCompare(gb);
    return a.localeCompare(b);
  });

  return (
    <main className="min-h-screen bg-navy-900">
      <div className="max-w-4xl mx-auto px-4 py-10 flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">WC 2026 Teams</h1>
            <p className="text-slate-400 text-sm mt-1">
              All {WC2026_TEAMS.size} qualified teams · Click to view profile
            </p>
          </div>
        </div>

        <div className="relative max-w-sm">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search teams…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg bg-navy-800 border border-navy-600 text-white pl-9 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-fifa-blue placeholder:text-slate-500"
          />
        </div>

        {filtered.length === 0 ? (
          <div className="text-slate-500 text-sm py-8 text-center">
            No teams match &ldquo;{search}&rdquo;
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {filtered.map((team) => {
              const group = getGroup(team);
              const isHost = HOST_TEAMS.has(team);
              return (
                <Link
                  key={team}
                  href={`/teams/${encodeURIComponent(team)}`}
                  className="bg-navy-800 border border-navy-600 rounded-xl p-4 flex flex-col items-center gap-2 hover:border-fifa-blue transition-colors group"
                >
                  <FlagIcon team={team} className="w-12 h-9 rounded" />
                  <span className="text-sm font-semibold text-white text-center leading-tight group-hover:text-fifa-blue-light transition-colors">
                    {team === "United States" ? "USA" : team}
                  </span>
                  <div className="flex items-center gap-1.5 flex-wrap justify-center">
                    {group && (
                      <span className="text-[10px] text-slate-500 tabular-nums">
                        Group {group}
                      </span>
                    )}
                    {isHost && (
                      <span className="text-[10px] text-gold-500">Host</span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
