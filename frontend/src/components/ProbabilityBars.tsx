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
    cardBg: string;
    cardBorder: string;
    textColor: string;
  }> = [
    {
      label: homeTeam,
      value: probabilities.home_win,
      color: "from-fifa-blue to-fifa-blue-light",
      ciKey: "home_win",
      cardBg: "bg-fifa-blue/[0.07]",
      cardBorder: "border-fifa-blue/25",
      textColor: "text-fifa-blue",
    },
    {
      label: "Draw",
      value: probabilities.draw,
      color: "from-slate-500 to-slate-400",
      ciKey: "draw",
      cardBg: "bg-white/[0.04]",
      cardBorder: "border-white/10",
      textColor: "text-slate-200",
    },
    {
      label: awayTeam,
      value: probabilities.away_win,
      color: "from-gold-dim to-gold-500",
      ciKey: "away_win",
      cardBg: "bg-gold-500/[0.06]",
      cardBorder: "border-gold-500/20",
      textColor: "text-gold-500",
    },
  ];

  const best = Math.max(probabilities.home_win, probabilities.draw, probabilities.away_win);

  const barsWithCi = bars.map((bar) => {
    const rawCi = confidence?.[bar.ciKey];
    const ci = rawCi
      ? ([
          Math.min(Math.max(rawCi[0], 0), 1),
          Math.min(Math.max(rawCi[1], rawCi[0]), 1),
        ] as [number, number])
      : undefined;
    const halfSpread = ci ? (((ci[1] - ci[0]) / 2) * 100).toFixed(1) : null;
    return { ...bar, ci, halfSpread };
  });

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Match Outcome</h3>
      {malformed && (
        <p className="text-xs text-amber-400">
          Warning: probabilities sum to {(sum * 100).toFixed(1)}% — data may be malformed.
        </p>
      )}

      {/* ── Mobile: 3-column card grid ── */}
      <div className="sm:hidden grid grid-cols-3 gap-2">
        {barsWithCi.map((bar, i) => {
          const isFavoured = bar.value === best;
          return (
            <div
              key={bar.label}
              className={`rounded-xl p-3 border ${bar.cardBg} ${
                isFavoured ? bar.cardBorder : "border-white/[0.06]"
              } flex flex-col gap-1.5`}
            >
              <span className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 truncate">
                {bar.label}
              </span>
              <span className={`font-anton text-[28px] leading-none tabular-nums ${bar.textColor}`}>
                {(bar.value * 100).toFixed(0)}%
              </span>
              {bar.halfSpread && (
                <span className="text-[9px] text-slate-500 tabular-nums">±{bar.halfSpread}%</span>
              )}
              <div className="mt-auto pt-1 h-1.5 bg-navy-700 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full rounded-full bg-gradient-to-r ${bar.color}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${(bar.value * 100).toFixed(1)}%` }}
                  transition={{ duration: 0.6, delay: i * 0.15, ease: "easeOut" }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Desktop: horizontal bar rows ── */}
      <div className="hidden sm:flex flex-col gap-3">
        {barsWithCi.map((bar, i) => (
          <div key={bar.label} className="flex items-center gap-3">
            <span className="w-32 text-sm text-slate-300 truncate text-right">{bar.label}</span>
            <div className="flex-1 bg-navy-600 rounded-full h-7 overflow-hidden relative">
              <motion.div
                className={`h-full rounded-full bg-gradient-to-r ${bar.color}`}
                initial={{ width: 0 }}
                animate={{ width: `${(bar.value * 100).toFixed(1)}%` }}
                transition={{ duration: 0.6, delay: i * 0.15, ease: "easeOut" }}
              />
              {bar.ci && (
                <div
                  className="absolute top-0 h-full bg-white/10 rounded-full"
                  style={{
                    left: `${(bar.ci[0] * 100).toFixed(2)}%`,
                    right: `${(100 - bar.ci[1] * 100).toFixed(2)}%`,
                  }}
                />
              )}
            </div>
            <span className="w-14 text-sm font-bold text-white text-right">
              {(bar.value * 100).toFixed(1)}%
            </span>
            {bar.halfSpread !== null ? (
              <span className="w-12 text-xs text-slate-400 text-right">±{bar.halfSpread}%</span>
            ) : (
              <span className="w-12" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
