"use client";
import { motion } from "framer-motion";
import type { Probabilities } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
}

export default function ProbabilityBars({ probabilities, homeTeam, awayTeam }: Props) {
  const bars = [
    { label: homeTeam, value: probabilities.home_win, color: "bg-pitch-400", glow: "shadow-pitch-400/50" },
    { label: "Draw", value: probabilities.draw, color: "bg-slate-500", glow: "" },
    { label: awayTeam, value: probabilities.away_win, color: "bg-gold-500", glow: "shadow-gold-500/50" },
  ];
  const max = Math.max(probabilities.home_win, probabilities.draw, probabilities.away_win);

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Match Outcome</h3>
      {bars.map((bar, i) => (
        <div key={bar.label} className="flex items-center gap-3">
          <span className="w-32 text-sm text-slate-300 truncate text-right">{bar.label}</span>
          <div className="flex-1 bg-navy-700 rounded-full h-7 overflow-hidden relative">
            <motion.div
              className={`h-full rounded-full ${bar.color} ${bar.value === max ? `shadow-lg ${bar.glow}` : ""}`}
              initial={{ width: 0 }}
              animate={{ width: `${(bar.value * 100).toFixed(1)}%` }}
              transition={{ duration: 0.6, delay: i * 0.15, ease: "easeOut" }}
            />
          </div>
          <span className="w-14 text-sm font-bold text-white text-right">
            {(bar.value * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}
