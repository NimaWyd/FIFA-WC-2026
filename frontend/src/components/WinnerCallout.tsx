"use client";
import FlagIcon from "@/components/FlagIcon";
import type { Probabilities } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
}

export default function WinnerCallout({ probabilities, homeTeam, awayTeam }: Props) {
  const { home_win, draw, away_win } = probabilities;

  let winnerLabel: string;
  let winnerPct: number;
  let isDraw: boolean;

  if (draw >= home_win && draw >= away_win) {
    winnerLabel = "Draw";
    winnerPct = draw;
    isDraw = true;
  } else if (home_win >= away_win) {
    winnerLabel = homeTeam;
    winnerPct = home_win;
    isDraw = false;
  } else {
    winnerLabel = awayTeam;
    winnerPct = away_win;
    isDraw = false;
  }

  return (
    <div className="flex flex-col gap-1 pb-4 mb-2 border-b border-slate-700/50">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Predicted Winner
      </span>
      <div className="flex items-center gap-3">
        {!isDraw && (
          <FlagIcon team={winnerLabel} className="w-10 h-7 rounded flex-shrink-0" />
        )}
        <span className="text-lg font-bold text-white">{winnerLabel}</span>
        <span className="text-lg font-bold text-[#d4af37]">
          {(winnerPct * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  );
}
