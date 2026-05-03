"use client";
import { WC2026_GROUPS, WCGroup } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";

interface Props {
  onSelectGroup: (group: WCGroup) => void;
}

const CONF_COLORS: Record<string, string> = {
  Mexico: "text-green-400",
  "United States": "text-blue-400",
  Canada: "text-red-400",
};

export default function GroupBracket({ onSelectGroup }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-200">Group Stage</h2>
        <span className="text-xs text-slate-500">12 groups · 48 teams</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {WC2026_GROUPS.map((group) => (
          <button
            key={group.id}
            onClick={() => onSelectGroup(group)}
            className="bg-[#0d1428] border border-slate-800 rounded-xl p-4 text-left hover:border-[#d4af37]/60 hover:bg-[#111d3c] transition-all group"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold tracking-widest text-[#d4af37] uppercase">
                Group {group.id}
              </span>
              <span className="text-xs text-slate-600 group-hover:text-slate-400 transition-colors">
                6 matches →
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {group.teams.map((team) => (
                <div key={team} className="flex items-center gap-2">
                  <FlagIcon team={team} className="w-5 h-3.5 rounded-sm flex-shrink-0" />
                  <span className={`text-sm font-medium ${CONF_COLORS[team] ?? "text-slate-300"}`}>
                    {team === "United States" ? "USA" : team}
                  </span>
                </div>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
