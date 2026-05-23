"use client";
import { motion } from "framer-motion";
import { WC2026_GROUPS, WCGroup } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";
import { displayName } from "@/lib/utils";

interface Props {
  onSelectGroup: (group: WCGroup) => void;
  showHeader?: boolean;
}

const HOSTS = new Set(["Mexico", "United States", "Canada"]);

const HOST_COLORS: Record<string, string> = {
  Mexico: "text-green-400",
  "United States": "text-blue-300",
  Canada: "text-red-400",
};

// Subtle per-group tint for the card gradient — cycles across 12 groups
const CARD_TINTS = [
  "from-[#1a3fff]/8",
  "from-[#0ea5e9]/8",
  "from-[#8b5cf6]/8",
  "from-[#10b981]/8",
  "from-[#ef4444]/8",
  "from-[#f59e0b]/8",
  "from-[#06b6d4]/8",
  "from-[#ec4899]/8",
  "from-[#3b82f6]/8",
  "from-[#a78bfa]/8",
  "from-[#14b8a6]/8",
  "from-[#f97316]/8",
];

export default function GroupBracket({ onSelectGroup, showHeader = true }: Props) {
  return (
    <div className="flex flex-col gap-6">
      {showHeader && (
        <div className="flex items-center justify-between">
          <h2 className="font-anton text-4xl text-white uppercase tracking-wide">Group Stage</h2>
          <span className="text-xs text-slate-500 tracking-widest uppercase">12 Groups · 48 Teams</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {WC2026_GROUPS.map((group, i) => (
          <motion.button
            key={group.id}
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.055, duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
            onClick={() => onSelectGroup(group)}
            className={`relative overflow-hidden bg-gradient-to-br ${CARD_TINTS[i]} to-navy-800 border border-navy-600 rounded-2xl p-5 text-left group hover:border-fifa-blue/50 hover:shadow-[0_0_36px_rgba(26,63,255,0.18)] transition-all duration-300 cursor-pointer`}
          >
            {/* Giant watermark letter */}
            <span className="pointer-events-none select-none absolute bottom-0 right-3 font-anton text-[120px] leading-none text-white/[0.035] group-hover:text-white/[0.07] transition-colors duration-300">
              {group.id}
            </span>

            {/* Glowing bottom bar — visible on hover */}
            <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-fifa-blue via-fifa-blue-light to-fifa-blue opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

            {/* Top row */}
            <div className="relative z-10 flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                {/* Group badge */}
                <span className="flex items-center justify-center w-7 h-7 rounded-md bg-fifa-blue/15 border border-fifa-blue/25 text-[11px] font-bold text-fifa-blue-light">
                  {group.id}
                </span>
                <span className="text-[11px] font-bold tracking-[0.22em] text-slate-400 uppercase">
                  Group {group.id}
                </span>
              </div>
              <span className="flex items-center gap-0.5 text-[11px] text-slate-600 group-hover:text-fifa-blue-light transition-colors duration-200">
                6 matches
                <svg
                  className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform duration-200"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                </svg>
              </span>
            </div>

            {/* Teams — 2 per row */}
            <div className="relative z-10 grid grid-cols-2 gap-y-2 gap-x-3">
              {group.teams.map((team) => (
                <div key={team} className="flex items-center gap-2 min-w-0">
                  <FlagIcon team={team} className="w-6 h-4 rounded-sm flex-shrink-0 shadow-sm" />
                  <span
                    className={`text-sm font-semibold truncate ${
                      HOST_COLORS[team] ?? "text-slate-200"
                    }`}
                  >
                    {displayName(team)}
                  </span>
                  {HOSTS.has(team) && (
                    <span className="ml-auto flex-shrink-0 text-[8px] font-bold text-gold-500 bg-gold-500/10 border border-gold-500/20 px-1.5 py-0.5 rounded tracking-wider">
                      HOST
                    </span>
                  )}
                </div>
              ))}
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
