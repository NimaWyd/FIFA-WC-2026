"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";
import { useSimulation } from "@/hooks/useSimulation";
import type { TeamSimResult } from "@/lib/types";

type SortKey = keyof Omit<TeamSimResult, "team" | "group">;

function ProbPill({ value }: { value: number }) {
  const pct = value * 100;
  const opacity = Math.max(0.08, value);
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-xs font-semibold text-white min-w-[48px] text-center"
      style={{ backgroundColor: `rgba(34,197,94,${opacity})` }}
    >
      {pct < 0.5 ? "<1%" : `${pct.toFixed(1)}%`}
    </span>
  );
}

const COLS: { key: SortKey; label: string }[] = [
  { key: "round_of_32",   label: "R32" },
  { key: "quarter_final", label: "QF" },
  { key: "semi_final",    label: "SF" },
  { key: "final",         label: "Final" },
  { key: "champion",      label: "🏆" },
];

export default function SimulationPanel() {
  const { data, loading, error } = useSimulation();
  const [sortKey, setSortKey] = useState<SortKey>("champion");
  const [sortAsc, setSortAsc] = useState(false);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-8 h-8 border-2 border-fifa-blue border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-sm">Running 1000 tournament simulations…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
        Simulation failed: {error}. Make sure the backend is running.
      </div>
    );
  }

  if (!data) return null;

  const sorted = [...data.teams].sort((a, b) => {
    const diff = a[sortKey] - b[sortKey];
    return sortAsc ? diff : -diff;
  });

  const podium = [...data.teams]
    .sort((a, b) => b.champion - a.champion)
    .slice(0, 5);

  function handleSort(key: SortKey) {
    if (key === sortKey) setSortAsc((v) => !v);
    else { setSortKey(key); setSortAsc(false); }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Champion podium */}
      <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Most Likely Champions · {data.n_simulations.toLocaleString()} Simulations
        </h2>
        <div className="flex gap-3 flex-wrap">
          {podium.map((t, i) => (
            <motion.div
              key={t.team}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="flex-1 min-w-[120px] bg-navy-700 border border-navy-600 rounded-xl p-3 flex flex-col items-center gap-2"
            >
              <FlagIcon team={t.team} className="w-12 h-9 rounded" />
              <span className="text-xs font-semibold text-white text-center leading-tight">{t.team}</span>
              <span className="text-lg font-black text-green-400">{(t.champion * 100).toFixed(1)}%</span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Full table */}
      <div className="bg-navy-800 rounded-2xl border border-navy-600 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-navy-600">
                <th className="text-left px-4 py-3 text-slate-400 font-semibold uppercase tracking-wider text-xs w-8">#</th>
                <th className="text-left px-4 py-3 text-slate-400 font-semibold uppercase tracking-wider text-xs">Team</th>
                <th className="text-center px-2 py-3 text-slate-400 font-semibold uppercase tracking-wider text-xs">Grp</th>
                {COLS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`text-center px-3 py-3 font-semibold uppercase tracking-wider text-xs cursor-pointer select-none transition-colors hover:text-white ${
                      sortKey === col.key ? "text-white" : "text-slate-400"
                    }`}
                  >
                    {col.label} {sortKey === col.key ? (sortAsc ? "↑" : "↓") : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((team, i) => (
                <tr
                  key={team.team}
                  className="border-b border-navy-700/50 hover:bg-navy-700/30 transition-colors"
                >
                  <td className="px-4 py-2.5 text-slate-500 text-xs">{i + 1}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <FlagIcon team={team.team} className="w-7 h-5 rounded" />
                      <span className="text-white font-medium truncate max-w-[130px]">{team.team}</span>
                    </div>
                  </td>
                  <td className="px-2 py-2.5 text-center text-slate-400 font-mono text-xs">{team.group}</td>
                  {COLS.map((col) => (
                    <td key={col.key} className="px-3 py-2.5 text-center">
                      <ProbPill value={team[col.key]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-2 border-t border-navy-700/50">
          <p className="text-xs text-slate-600">
            Based on {data.n_simulations.toLocaleString()} Monte Carlo simulations · Generated {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}
