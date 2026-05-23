"use client";
import { motion } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";
import { displayName } from "@/lib/utils";

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

type ZoneConfig = {
  label: string;
  labelColor: string;
  rowBg: string;
  leftBar: string;
  rankColor: string;
  ptsColor: string;
};

const ZONE: ZoneConfig[] = [
  {
    label: "ADV",
    labelColor: "text-pitch-300",
    rowBg: "bg-pitch-500/[0.07]",
    leftBar: "bg-pitch-400",
    rankColor: "text-white",
    ptsColor: "text-white",
  },
  {
    label: "ADV",
    labelColor: "text-pitch-300",
    rowBg: "bg-pitch-500/[0.07]",
    leftBar: "bg-pitch-400",
    rankColor: "text-white",
    ptsColor: "text-white",
  },
  {
    label: "3RD?",
    labelColor: "text-amber-400",
    rowBg: "bg-amber-400/[0.04]",
    leftBar: "bg-amber-400/50",
    rankColor: "text-slate-300",
    ptsColor: "text-slate-300",
  },
  {
    label: "OUT",
    labelColor: "text-slate-600",
    rowBg: "",
    leftBar: "bg-transparent",
    rankColor: "text-slate-500",
    ptsColor: "text-slate-500",
  },
];

export default function GroupStandings({ standings, groupId }: Props) {
  const sorted = [...standings].sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.gd !== a.gd) return b.gd - a.gd;
    return b.gf - a.gf;
  });

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-bold tracking-[0.22em] text-slate-500 uppercase">
          Group {groupId} · Predicted Standings
        </h3>
        <span className="text-[10px] text-slate-600 bg-navy-800 border border-navy-600 px-2 py-0.5 rounded-full">
          AI Simulation
        </span>
      </div>

      <div className="rounded-xl overflow-hidden border border-navy-600 bg-navy-800">
        {/* Table header */}
        <div className="grid grid-cols-[3px_28px_1fr_repeat(6,_32px)] px-3 py-2.5 text-[10px] font-bold text-slate-600 uppercase tracking-widest border-b border-navy-600 bg-navy-900/70">
          <span />
          <span className="text-center">#</span>
          <span className="pl-1">Team</span>
          <span className="text-center">P</span>
          <span className="text-center">W</span>
          <span className="text-center">D</span>
          <span className="text-center">L</span>
          <span className="text-center">GD</span>
          <span className="text-center">Pts</span>
        </div>

        {sorted.map((s, i) => {
          const zone = ZONE[i] ?? ZONE[3];
          const gdSign = s.gd > 0 ? "+" : "";

          return (
            <motion.div
              key={s.team}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.07, duration: 0.32, ease: "easeOut" }}
              className={`grid grid-cols-[3px_28px_1fr_repeat(6,_32px)] px-3 py-3 items-center border-b border-navy-600/40 last:border-0 ${zone.rowBg}`}
            >
              {/* Left zone bar */}
              <span className={`self-stretch w-[3px] rounded-full ${zone.leftBar}`} />

              {/* Rank */}
              <span className={`text-xs font-bold text-center ${zone.rankColor}`}>
                {i + 1}
              </span>

              {/* Team */}
              <div className="flex items-center gap-2 min-w-0 pl-1">
                <FlagIcon team={s.team} className="w-5 h-3.5 rounded-sm flex-shrink-0" />
                <span
                  className={`text-xs font-semibold truncate ${
                    i < 2 ? "text-white" : "text-slate-400"
                  }`}
                >
                  {displayName(s.team)}
                </span>
                <span className={`text-[9px] font-bold flex-shrink-0 ${zone.labelColor}`}>
                  {zone.label}
                </span>
              </div>

              {/* Stats */}
              <span className="text-center text-[11px] text-slate-500">{s.played}</span>
              <span className="text-center text-[11px] text-slate-500">{s.won}</span>
              <span className="text-center text-[11px] text-slate-500">{s.drawn}</span>
              <span className="text-center text-[11px] text-slate-500">{s.lost}</span>
              <span
                className={`text-center text-[11px] font-medium ${
                  s.gd > 0
                    ? "text-pitch-300"
                    : s.gd < 0
                    ? "text-red-400"
                    : "text-slate-500"
                }`}
              >
                {gdSign}{s.gd}
              </span>
              <span className={`text-center text-sm font-bold tabular-nums ${zone.ptsColor}`}>
                {s.points}
              </span>
            </motion.div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 pt-0.5">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-pitch-400/30 border-l-2 border-pitch-400" />
          <span className="text-[10px] text-slate-600">Advance to Round of 32</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-amber-400/10 border-l-2 border-amber-400/50" />
          <span className="text-[10px] text-slate-600">Best 3rd place may advance</span>
        </div>
      </div>
    </div>
  );
}
