"use client";

import { motion } from "framer-motion";
import { UserGroupIcon, UserIcon } from "@heroicons/react/24/solid";
import rostersData from "@/lib/rosters.json";

interface Player {
  name: string;
  club: string;
  age?: number;
}

interface TeamRoster {
  manager: string;
  goalkeepers: Player[];
  defenders: Player[];
  midfielders: Player[];
  forwards: Player[];
}

interface UnreleasedRoster {
  released: false;
  manager?: string;
}

type RosterEntry = TeamRoster | UnreleasedRoster;

const rosters = rostersData as Record<string, RosterEntry>;

const POSITIONS: { key: keyof TeamRoster; label: string; color: string }[] = [
  { key: "goalkeepers", label: "Goalkeepers", color: "text-yellow-400" },
  { key: "defenders",   label: "Defenders",   color: "text-sky-400"    },
  { key: "midfielders", label: "Midfielders", color: "text-emerald-400" },
  { key: "forwards",    label: "Forwards",    color: "text-red-400"    },
];

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

function PlayerCard({ player }: { player: Player }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-navy-700/60 border border-navy-600/60 hover:border-navy-500 transition-colors">
      <div className="w-7 h-7 rounded-full bg-navy-600 border border-navy-500 flex items-center justify-center flex-shrink-0">
        <UserIcon className="w-3.5 h-3.5 text-slate-400" />
      </div>
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-sm font-semibold text-white leading-tight truncate">{player.name}</span>
        <span className="text-xs text-slate-400 truncate">{player.club}</span>
      </div>
      {player.age != null && player.age > 0 && (
        <span className="flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded bg-navy-600 border border-navy-500 text-slate-400 tabular-nums">
          {player.age}
        </span>
      )}
    </div>
  );
}

function PositionGroup({
  label,
  color,
  players,
}: {
  label: string;
  color: string;
  players: Player[];
}) {
  if (players.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className={`text-[10px] font-bold tracking-[0.18em] uppercase ${color}`}>
          {label}
        </span>
        <span className="text-[10px] text-slate-600 font-medium">· {players.length}</span>
        <div className="flex-1 h-px bg-navy-600" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
        {players.map((p) => (
          <PlayerCard key={p.name} player={p} />
        ))}
      </div>
    </div>
  );
}

export default function RosterSection({ team }: { team: string }) {
  const entry = rosters[team];

  if (!entry) return null;

  const isUnreleased = "released" in entry && entry.released === false;

  return (
    <motion.div variants={fadeUp} className="bg-navy-800 rounded-2xl border border-navy-600 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-navy-600 flex items-center gap-3">
        <UserGroupIcon className="h-4 w-4 text-slate-500" />
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Squad</h2>
      </div>

      {isUnreleased ? (
        /* Not yet announced */
        <div className="px-6 py-10 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-full bg-navy-700 border border-navy-600 flex items-center justify-center">
            <UserGroupIcon className="w-6 h-6 text-slate-600" />
          </div>
          <p className="text-slate-400 font-semibold text-sm">Squad not yet announced</p>
          <p className="text-slate-600 text-xs max-w-xs">
            {team}&apos;s official WC 2026 squad hasn&apos;t been released yet. Final squads must be submitted by June 1.
          </p>
          {(entry as UnreleasedRoster).manager && (
            <div className="mt-2 flex items-center gap-2 px-4 py-2 rounded-lg bg-navy-700 border border-navy-600">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Head Coach</span>
              <span className="text-sm text-white font-semibold">{(entry as UnreleasedRoster).manager}</span>
            </div>
          )}
        </div>
      ) : (
        /* Full roster */
        <div className="px-6 py-5 flex flex-col gap-6">
          {/* Manager */}
          {(entry as TeamRoster).manager && (
            <div className="flex items-center gap-3 p-3 rounded-xl bg-navy-700/50 border border-navy-600">
              <div className="w-8 h-8 rounded-full bg-gold-500/10 border border-gold-500/30 flex items-center justify-center flex-shrink-0">
                <UserIcon className="w-4 h-4 text-gold-500" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Head Coach</span>
                <span className="text-sm font-bold text-white">{(entry as TeamRoster).manager}</span>
              </div>
            </div>
          )}

          {/* Position groups */}
          {POSITIONS.map(({ key, label, color }) => (
            <PositionGroup
              key={key}
              label={label}
              color={color}
              players={(entry as TeamRoster)[key] as Player[]}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
