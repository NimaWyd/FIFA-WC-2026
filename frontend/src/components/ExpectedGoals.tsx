"use client";
import FlagIcon from "@/components/FlagIcon";
import { displayName } from "@/lib/utils";

interface Props {
  xg: { home: number; away: number };
  homeTeam: string;
  awayTeam: string;
}

export default function ExpectedGoals({ xg, homeTeam, awayTeam }: Props) {
  const total = xg.home + xg.away;
  const homePct = total === 0 ? 50 : (xg.home / total) * 100;

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-[11px] font-bold tracking-[0.22em] text-slate-500 uppercase">
        Expected Goals (xG)
      </h3>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <div className="flex flex-col items-center gap-2">
          <FlagIcon team={homeTeam} className="w-10 h-7 rounded-sm shadow" />
          <div className="font-anton text-5xl text-fifa-blue-light tabular-nums leading-none">
            {xg.home.toFixed(2)}
          </div>
          <div className="text-[11px] text-slate-500 truncate max-w-[110px] text-center">
            {displayName(homeTeam)}
          </div>
        </div>
        <div className="font-anton text-xl text-navy-600 tracking-widest">xG</div>
        <div className="flex flex-col items-center gap-2">
          <FlagIcon team={awayTeam} className="w-10 h-7 rounded-sm shadow" />
          <div className="font-anton text-5xl text-gold-500 tabular-nums leading-none">
            {xg.away.toFixed(2)}
          </div>
          <div className="text-[11px] text-slate-500 truncate max-w-[110px] text-center">
            {displayName(awayTeam)}
          </div>
        </div>
      </div>
      <div className="flex h-1.5 rounded-full overflow-hidden">
        <div className="bg-fifa-blue transition-all duration-500" style={{ width: `${homePct}%` }} />
        <div className="bg-gold-500 flex-1" />
      </div>
    </div>
  );
}
