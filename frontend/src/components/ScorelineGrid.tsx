"use client";
import { motion } from "framer-motion";
import type { Scoreline } from "@/lib/types";

interface Props {
  scorelines: Scoreline[];
}

export default function ScorelineGrid({ scorelines }: Props) {
  if (!scorelines || scorelines.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        <h3 className="text-[11px] font-bold tracking-[0.22em] text-slate-500 uppercase">Top Scorelines</h3>
        <p className="text-slate-500 text-sm">No scoreline probabilities available.</p>
      </div>
    );
  }

  const [top, ...rest] = scorelines;
  const max = Math.max(...scorelines.map((s) => s.probability));
  const safeMax = max > 0 ? max : 1;

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-[11px] font-bold tracking-[0.22em] text-slate-500 uppercase">Top Scorelines</h3>

      {/* Featured top scoreline */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-fifa-blue/10 to-navy-700 border border-fifa-blue/30 p-5 flex flex-col items-center gap-3">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-fifa-blue/60 to-transparent" />
        <span className="text-[10px] font-bold tracking-[0.25em] text-fifa-blue uppercase">Most Likely</span>
        <div className="font-anton text-6xl text-white tracking-widest tabular-nums">{top.scoreline}</div>
        <div className="flex items-center gap-3">
          <div className="w-28 h-1 bg-navy-900 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-fifa-blue rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${(top.probability / safeMax) * 100}%` }}
              transition={{ duration: 0.7, ease: "easeOut" }}
            />
          </div>
          <span className="text-sm font-bold text-fifa-blue-light tabular-nums">
            {(top.probability * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Remaining scorelines compact grid */}
      {rest.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {rest.map((s) => (
            <div
              key={s.scoreline}
              className="flex flex-col items-center justify-center rounded-xl py-3 px-2 bg-navy-700 border border-navy-600"
            >
              <span className="text-xl font-bold text-white tabular-nums">{s.scoreline}</span>
              <span className="text-xs text-slate-500 mt-1 tabular-nums">{(s.probability * 100).toFixed(1)}%</span>
              <div className="w-full bg-navy-600 rounded-full h-0.5 mt-1.5">
                <div
                  className="h-0.5 rounded-full bg-slate-500"
                  style={{ width: `${(s.probability / safeMax) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
