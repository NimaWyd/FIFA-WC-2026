"use client";
import FlagIcon from "@/components/FlagIcon";

export type Standing = {
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
};

interface Props {
  standings: Standing[];
  groupId: string;
}

export default function GroupStandings({ standings, groupId }: Props) {
  const sorted = [...standings].sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.gd !== a.gd) return b.gd - a.gd;
    return b.gf - a.gf;
  });

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
        Group {groupId} Standings
      </h3>
      <div className="bg-[#0d1428] border border-slate-800 rounded-xl overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[auto_1fr_repeat(7,_auto)] gap-x-4 px-4 py-2 text-[10px] font-bold text-slate-500 uppercase tracking-wider border-b border-slate-800">
          <span>#</span>
          <span>Team</span>
          <span className="text-center">P</span>
          <span className="text-center">W</span>
          <span className="text-center">D</span>
          <span className="text-center">L</span>
          <span className="text-center">GF</span>
          <span className="text-center">GA</span>
          <span className="text-center font-bold">Pts</span>
        </div>

        {sorted.map((s, i) => (
          <div
            key={s.team}
            className={`grid grid-cols-[auto_1fr_repeat(7,_auto)] gap-x-4 px-4 py-3 items-center text-sm border-b border-slate-800/50 last:border-0 ${
              i < 2 ? "bg-[#111d3c]/40" : ""
            }`}
          >
            <span
              className={`text-xs font-bold w-4 text-center ${
                i < 2 ? "text-[#d4af37]" : i === 2 ? "text-slate-400" : "text-slate-500"
              }`}
            >
              {i + 1}
            </span>
            <div className="flex items-center gap-2 min-w-0">
              <FlagIcon team={s.team} className="w-5 h-3.5 rounded-sm flex-shrink-0" />
              <span className="text-slate-200 font-medium truncate text-xs">
                {s.team === "United States" ? "USA" : s.team}
              </span>
              {i < 2 && (
                <span className="text-[9px] text-[#d4af37]/70 flex-shrink-0">ADV</span>
              )}
              {i === 2 && (
                <span className="text-[9px] text-amber-400/70 flex-shrink-0">3RD?</span>
              )}
            </div>
            <span className="text-center text-slate-400 text-xs">{s.played}</span>
            <span className="text-center text-slate-400 text-xs">{s.won}</span>
            <span className="text-center text-slate-400 text-xs">{s.drawn}</span>
            <span className="text-center text-slate-400 text-xs">{s.lost}</span>
            <span className="text-center text-slate-400 text-xs">{s.gf}</span>
            <span className="text-center text-slate-400 text-xs">{s.ga}</span>
            <span
              className={`text-center text-xs font-bold ${
                i < 2 ? "text-[#d4af37]" : "text-white"
              }`}
            >
              {s.points}
            </span>
          </div>
        ))}
      </div>
      <p className="text-[10px] text-slate-600">
        Top 2 advance automatically · Best 8 third-place teams across all groups also advance
      </p>
    </div>
  );
}
