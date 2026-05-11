"use client";
import { motion } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";
import type { Probabilities } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
}

const R = 40;
const C = 2 * Math.PI * R;
const SIZE = 100;

const COLORS = {
  home: "#1a3fff",
  away: "#f5c842",
  draw: "#94a3b8",
} as const;

interface RingProps {
  confidence: number;
  color: string;
  isDraw: boolean;
  team?: string;
}

function ConfidenceRing({ confidence, color, isDraw, team }: RingProps) {
  return (
    <div className="relative flex-shrink-0" style={{ width: SIZE, height: SIZE }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        <circle
          r={R}
          cx={SIZE / 2}
          cy={SIZE / 2}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={5}
        />
        <motion.circle
          r={R}
          cx={SIZE / 2}
          cy={SIZE / 2}
          fill="none"
          stroke={color}
          strokeWidth={5}
          strokeLinecap="round"
          strokeDasharray={C}
          initial={{ strokeDashoffset: C }}
          animate={{ strokeDashoffset: C * (1 - confidence) }}
          transition={{ duration: 0.9, ease: "easeOut" }}
          style={{ rotate: -90, transformOrigin: "50% 50%" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        {isDraw ? (
          <span className="text-2xl font-bold text-slate-300">½</span>
        ) : team ? (
          <FlagIcon team={team} className="w-12 h-8 rounded" />
        ) : null}
      </div>
    </div>
  );
}

export default function WinnerCallout({ probabilities, homeTeam, awayTeam }: Props) {
  const { home_win, draw, away_win } = probabilities;

  let winnerLabel: string;
  let winnerPct: number;
  let isDraw: boolean;
  let color: string;

  if (draw >= home_win && draw >= away_win) {
    winnerLabel = "Draw";
    winnerPct = draw;
    isDraw = true;
    color = COLORS.draw;
  } else if (home_win >= away_win) {
    winnerLabel = homeTeam;
    winnerPct = home_win;
    isDraw = false;
    color = COLORS.home;
  } else {
    winnerLabel = awayTeam;
    winnerPct = away_win;
    isDraw = false;
    color = COLORS.away;
  }

  const displayName =
    winnerLabel === "Draw" ? "Draw"
    : winnerLabel === "United States" ? "USA"
    : winnerLabel;

  return (
    <div className="flex flex-col items-center gap-4">
      <span className="text-[10px] font-bold tracking-[0.3em] text-slate-500 uppercase">
        Predicted Winner
      </span>

      <div className="relative">
        <div
          className="absolute inset-0 rounded-full blur-2xl opacity-25 scale-[2.5]"
          style={{ background: color }}
        />
        <ConfidenceRing
          confidence={winnerPct}
          color={color}
          isDraw={isDraw}
          team={isDraw ? undefined : winnerLabel}
        />
      </div>

      <div className="text-center">
        <div className="font-anton text-4xl text-white leading-none">{displayName}</div>
        <div className="text-3xl font-black tabular-nums mt-1.5" style={{ color }}>
          {(winnerPct * 100).toFixed(1)}%
        </div>
        <div className="text-[9px] font-bold tracking-[0.3em] text-slate-600 uppercase mt-2">
          Win probability
        </div>
      </div>
    </div>
  );
}
