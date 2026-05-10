"use client";
import { motion } from "framer-motion";
import type { Probabilities, ConfidenceInterval } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
  confidence?: ConfidenceInterval;
}

export default function ProbabilityBars({ probabilities, homeTeam, awayTeam, confidence }: Props) {
  const sum = probabilities.home_win + probabilities.draw + probabilities.away_win;
  const malformed = Math.abs(sum - 1.0) > 0.01;

  const bars: Array<{
    label: string;
    value: number;
    color: string;
    ciKey: keyof ConfidenceInterval;
  }> = [
    { label: homeTeam, value: probabilities.home_win, color: "from-fifa-blue to-fifa-blue-light", ciKey: "home_win" },
    { label: "Draw",   value: probabilities.draw,     color: "from-slate-500 to-slate-400",       ciKey: "draw" },
    { label: awayTeam, value: probabilities.away_win, color: "from-gold-dim to-gold-500",         ciKey: "away_win" },
  ];

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Match Outcome</h3>
      {malformed && (
        <p className="text-xs text-amber-400">
          Warning: probabilities sum to {(sum * 100).toFixed(1)}% — data may be malformed.
        </p>
      )}
      {bars.map((bar, i) => {
        const ci = confidence?.[bar.ciKey] as [number, number] | undefined;
        const halfSpread = ci ? (((ci[1] - ci[0]) / 2) * 100).toFixed(1) : null;

        return (
          <div key={bar.label} className="flex items-center gap-3">
            <span className="w-32 text-sm text-slate-300 truncate text-right">{bar.label}</span>
            <div className="flex-1 bg-navy-600 rounded-full h-7 overflow-hidden relative">
              {ci && (
                <div
                  className="absolute top-0 h-full bg-white/10 rounded-full"
                  style={{
                    left: `${(ci[0] * 100).toFixed(2)}%`,
                    right: `${(100 - ci[1] * 100).toFixed(2)}%`,
                  }}
                />
              )}
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
            {halfSpread !== null ? (
              <span className="w-12 text-xs text-slate-400 text-right">±{halfSpread}%</span>
            ) : (
              <span className="w-12" />
            )}
          </div>
        );
      })}
    </div>
  );
}
