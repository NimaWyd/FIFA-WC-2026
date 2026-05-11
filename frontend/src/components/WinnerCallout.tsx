"use client";
import { motion } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";
import type { Probabilities } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
}

const R = 28;
const C = 2 * Math.PI * R;
const SIZE = 72;

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
        {/* Track */}
        <circle
          r={R}
          cx={SIZE / 2}
          cy={SIZE / 2}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={4}
        />
        {/* Animated arc */}
        <motion.circle
          r={R}
          cx={SIZE / 2}
          cy={SIZE / 2}
          fill="none"
          stroke={color}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={C}
          initial={{ strokeDashoffset: C }}
          animate={{ strokeDashoffset: C * (1 - confidence) }}
          transition={{ duration: 0.9, ease: "easeOut" }}
          style={{ rotate: -90, transformOrigin: "50% 50%" }}
        />
      </svg>
      {/* Centred content */}
      <div className="absolute inset-0 flex items-center justify-center">
        {isDraw ? (
          <span className="text-xl font-bold text-slate-300">½</span>
        ) : team ? (
          <FlagIcon team={team} className="w-10 h-7 rounded" />
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

  return (
    <div className="flex flex-col gap-1 pb-4 mb-2 border-b border-navy-600">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Predicted Winner
      </span>
      <div className="flex items-center gap-4">
        <ConfidenceRing
          confidence={winnerPct}
          color={color}
          isDraw={isDraw}
          team={isDraw ? undefined : winnerLabel}
        />
        <div className="flex flex-col gap-0.5">
          <span className="text-lg font-bold text-white">{winnerLabel}</span>
          <span className="text-2xl font-black tabular-nums" style={{ color }}>
            {(winnerPct * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}
