"use client";

interface Props {
  xg: { home: number; away: number };
  homeTeam: string;
  awayTeam: string;
}

export default function ExpectedGoals({ xg, homeTeam, awayTeam }: Props) {
  const total = xg.home + xg.away;
  const homePct = total === 0 ? 50 : (xg.home / total) * 100;

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Expected Goals (xG)</h3>
      <div className="flex items-center justify-between gap-6">
        <div className="flex-1 text-center">
          <div className="text-4xl font-bold text-pitch-300">{xg.home.toFixed(2)}</div>
          <div className="text-sm text-slate-400 mt-1 truncate">{homeTeam}</div>
        </div>
        <div className="text-slate-500 font-bold text-xl">vs</div>
        <div className="flex-1 text-center">
          <div className="text-4xl font-bold text-gold-400">{xg.away.toFixed(2)}</div>
          <div className="text-sm text-slate-400 mt-1 truncate">{awayTeam}</div>
        </div>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden">
        <div className="bg-pitch-400 transition-all duration-500" style={{ width: `${homePct}%` }} />
        <div className="bg-gold-500 flex-1" />
      </div>
    </div>
  );
}
