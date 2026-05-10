"use client";
import FlagIcon from "@/components/FlagIcon";

interface Props {
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  compact?: boolean;
}

function teamLabel(name: string) {
  return name === "United States" ? "USA" : name;
}

export default function MatchScoreboard({ homeTeam, awayTeam, homeGoals, awayGoals, compact = false }: Props) {
  if (compact) {
    return (
      <div className="flex items-center gap-1 bg-navy-700 rounded-lg px-2.5 py-1 border border-gold-500/40 flex-shrink-0">
        <span className="text-sm font-bold text-gold-500 w-4 text-center tabular-nums">{homeGoals}</span>
        <span className="text-slate-500 text-xs">–</span>
        <span className="text-sm font-bold text-gold-500 w-4 text-center tabular-nums">{awayGoals}</span>
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
        <div className="flex items-center gap-3 px-8 py-4 bg-navy-700 rounded-2xl border border-gold-500/40">
          <span className="text-5xl font-black tabular-nums bg-gradient-to-br from-white to-gold-500 bg-clip-text text-transparent">
            {homeGoals}
          </span>
          <span className="text-3xl text-slate-500 font-light">–</span>
          <span className="text-5xl font-black tabular-nums bg-gradient-to-br from-white to-gold-500 bg-clip-text text-transparent">
            {awayGoals}
          </span>
        </div>
        <div className="flex-1 flex flex-col items-center gap-2">
          <FlagIcon team={awayTeam} className="w-16 h-12 rounded" />
          <span className="text-sm font-semibold text-white text-center">{teamLabel(awayTeam)}</span>
        </div>
      </div>
    </div>
  );
}
