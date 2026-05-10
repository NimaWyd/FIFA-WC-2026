"use client";
import { motion } from "framer-motion";
import type { Probabilities } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
}

export default function ProbabilityBars({ probabilities, homeTeam, awayTeam }: Props) {
  const sum = probabilities.home_win + probabilities.draw + probabilities.away_win;
  const malformed = Math.abs(sum - 1.0) > 0.01;

  const bars = [
    { label: homeTeam, value: probabilities.home_win, color: "from-fifa-blue to-fifa-blue-light" },
    { label: "Draw",   value: probabilities.draw,     color: "from-slate-500 to-slate-400" },
    { label: awayTeam, value: probabilities.away_win, color: "from-gold-dim to-gold-500" },
  ];

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Match Outcome</h3>
      {malformed && (
        <p className="text-xs text-amber-400">
          Warning: probabilities sum to {(sum * 100).toFixed(1)}% — data may be malformed.
        </p>
      )}
      {bars.map((bar, i) => (
        <div key={bar.label} className="flex items-center gap-3">
          <span className="w-32 text-sm text-slate-300 truncate text-right">{bar.label}</span>
          <div className="flex-1 bg-navy-600 rounded-full h-7 overflow-hidden relative">
            <motion.div
              className={`h-full rounded-full bg-gradient-to-r ${bar.color}`}
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
