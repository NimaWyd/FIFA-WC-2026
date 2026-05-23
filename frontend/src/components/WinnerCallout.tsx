"use client";
import { motion } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";
import type { Probabilities } from "@/lib/types";
import { displayName } from "@/lib/utils";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
}

const R = 40;
const C = 2 * Math.PI * R;
const VIEWBOX = 100;

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
    /* w/h set via parent class — SVG fills 100% so it scales with the container */
    <div className="relative w-full h-full">
      <svg width="100%" height="100%" viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}>
        <circle
          r={R}
          cx={VIEWBOX / 2}
          cy={VIEWBOX / 2}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={5}
        />
        <motion.circle
          r={R}
          cx={VIEWBOX / 2}
          cy={VIEWBOX / 2}
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

  const winnerDisplayName =
    winnerLabel === "Draw" ? "Draw"
    : displayName(winnerLabel);

  return (
    <div className="w-full flex flex-col items-center gap-4 py-2">
      <span className="text-[10px] font-bold tracking-[0.3em] text-slate-500 uppercase text-center">
        Predicted Winner
      </span>

      {/* Ring — 120px on mobile, 100px on sm+ */}
      <div className="relative w-[120px] h-[120px] sm:w-[100px] sm:h-[100px] flex-shrink-0">
        <div
          className="absolute inset-0 rounded-full blur-2xl opacity-25 scale-[2.2]"
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
        <div className="font-anton text-4xl sm:text-4xl text-white leading-none">{winnerDisplayName}</div>
        <div className="text-4xl sm:text-3xl font-black tabular-nums mt-1.5" style={{ color }}>
          {(winnerPct * 100).toFixed(1)}%
        </div>
        <div className="text-[9px] font-bold tracking-[0.3em] text-slate-600 uppercase mt-2">
          Win probability
        </div>
      </div>
    </div>
  );
}
