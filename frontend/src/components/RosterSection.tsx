"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { UserGroupIcon, UserIcon } from "@heroicons/react/24/solid";
import rostersData from "@/lib/rosters.json";

interface Player {
  name: string;
  club: string;
  age?: number;
  espn_id?: string;
  sofascore_id?: string;
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

const POSITIONS: { key: keyof TeamRoster; label: string; accent: string }[] = [
  { key: "goalkeepers", label: "Goalkeepers", accent: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10" },
  { key: "defenders",   label: "Defenders",   accent: "text-sky-400 border-sky-400/30 bg-sky-400/10"         },
  { key: "midfielders", label: "Midfielders", accent: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10" },
  { key: "forwards",    label: "Forwards",    accent: "text-red-400 border-red-400/30 bg-red-400/10"         },
];

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0][0]?.toUpperCase() ?? "?";
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function PlayerPhoto({ player, accent }: { player: Player; accent: string }) {
  // 0 = sofascore, 1 = espn, 2 = initials
  const [stage, setStage] = useState(0);

  const sofascoreUrl = player.sofascore_id
    ? `https://api.sofascore.com/api/v1/player/${player.sofascore_id}/image`
    : null;
  const espnUrl = player.espn_id
    ? `https://a.espncdn.com/i/headshots/soccer/players/full/${player.espn_id}.png`
    : null;

  const photoUrl = stage === 0 ? sofascoreUrl : stage === 1 ? espnUrl : null;

  const handleError = () => {
    if (stage === 0 && espnUrl) setStage(1);
    else setStage(2);
  };

  if (photoUrl && stage < 2) {
    return (
      <div className="relative w-14 h-14 rounded-xl overflow-hidden flex-shrink-0 bg-navy-700 border border-navy-600">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={photoUrl}
          alt={player.name}
          className="w-full h-full object-cover object-top"
          onError={handleError}
        />
      </div>
    );
  }

  return (
    <div className={`w-14 h-14 rounded-xl flex-shrink-0 flex items-center justify-center border ${accent} font-bold text-base`}>
      {getInitials(player.name)}
    </div>
  );
}

function PlayerCard({ player, accent }: { player: Player; accent: string }) {
  return (
    <div className="flex items-center gap-3 p-2.5 rounded-xl bg-navy-700/50 border border-navy-600/60 hover:border-navy-500 hover:bg-navy-700 transition-all duration-150">
      <PlayerPhoto player={player} accent={accent} />
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-sm font-semibold text-white leading-tight truncate">{player.name}</span>
        <span className="text-xs text-slate-400 truncate mt-0.5">{player.club}</span>
        {player.age != null && (
          <span className="text-[10px] text-slate-500 mt-0.5">Age {player.age}</span>
        )}
      </div>
    </div>
  );
}

function PositionGroup({ label, accent, players }: {
  label: string;
  accent: string;
  players: Player[];
}) {
  if (players.length === 0) return null;
  const [textClass] = accent.split(" ");
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center gap-2">
        <span className={`text-[10px] font-bold tracking-[0.18em] uppercase ${textClass}`}>
          {label}
        </span>
        <span className="text-[10px] text-slate-600 font-medium">· {players.length}</span>
        <div className="flex-1 h-px bg-navy-600" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {players.map((p) => (
          <PlayerCard key={p.name} player={p} accent={accent} />
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
        {!isUnreleased && (
          <span className="ml-auto text-[10px] text-slate-600">
            {["goalkeepers","defenders","midfielders","forwards"]
              .reduce((sum, k) => sum + ((entry as TeamRoster)[k as keyof TeamRoster] as Player[]).length, 0)} players
          </span>
        )}
      </div>

      {isUnreleased ? (
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
        <div className="px-6 py-5 flex flex-col gap-6">
          {/* Manager */}
          {(entry as TeamRoster).manager && (
            <div className="flex items-center gap-3 p-3 rounded-xl bg-navy-700/50 border border-navy-600">
              <div className="w-10 h-10 rounded-full bg-gold-500/10 border border-gold-500/30 flex items-center justify-center flex-shrink-0">
                <UserIcon className="w-5 h-5 text-gold-500" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Head Coach</span>
                <span className="text-sm font-bold text-white">{(entry as TeamRoster).manager}</span>
              </div>
            </div>
          )}

          {/* Position groups */}
          {POSITIONS.map(({ key, label, accent }) => (
            <PositionGroup
              key={key}
              label={label}
              accent={accent}
              players={(entry as TeamRoster)[key] as Player[]}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
