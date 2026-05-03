"use client";
import FlagIcon from "@/components/FlagIcon";

interface Props {
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  /** compact=true renders a score-only pill for fixture cards; default is full scoreboard */
  compact?: boolean;
}

function teamLabel(name: string) {
  return name === "United States" ? "USA" : name;
}

export default function MatchScoreboard({
  homeTeam,
  awayTeam,
  homeGoals,
  awayGoals,
  compact = false,
}: Props) {
  if (compact) {
    // Score-only pill — team names/flags are already shown by the parent fixture card
    return (
      <div className="flex items-center gap-1 bg-[#111d3c] rounded-lg px-2.5 py-1 border border-[#d4af37]/40 flex-shrink-0">
        <span className="text-sm font-bold text-[#d4af37] w-4 text-center tabular-nums">{homeGoals}</span>
        <span className="text-slate-500 text-xs">–</span>
        <span className="text-sm font-bold text-[#d4af37] w-4 text-center tabular-nums">{awayGoals}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Predicted Score</h3>
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 flex flex-col items-center gap-2">
          <FlagIcon team={homeTeam} className="w-16 h-12 rounded" />
          <span className="text-sm font-semibold text-white text-center">{teamLabel(homeTeam)}</span>
        </div>
        <div className="flex items-center gap-3 px-8 py-4 bg-[#111d3c] rounded-2xl border border-[#d4af37]/40">
          <span className="text-5xl font-bold text-[#d4af37] tabular-nums">{homeGoals}</span>
          <span className="text-3xl text-slate-500 font-light">–</span>
          <span className="text-5xl font-bold text-[#d4af37] tabular-nums">{awayGoals}</span>
        </div>
        <div className="flex-1 flex flex-col items-center gap-2">
          <FlagIcon team={awayTeam} className="w-16 h-12 rounded" />
          <span className="text-sm font-semibold text-white text-center">{teamLabel(awayTeam)}</span>
        </div>
      </div>
    </div>
  );
}
