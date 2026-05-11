"use client";
import { WC2026_GROUPS, WCGroup } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";

interface Props {
  onSelectGroup: (group: WCGroup) => void;
  showHeader?: boolean;
}

const HOST_COLORS: Record<string, string> = {
  Mexico: "text-green-400",
  "United States": "text-blue-400",
  Canada: "text-red-400",
};

export default function GroupBracket({ onSelectGroup, showHeader = true }: Props) {
  return (
    <div className="flex flex-col gap-4">
      {showHeader && (
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Group Stage</h2>
          <span className="text-xs text-slate-500">12 groups · 48 teams</span>
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {WC2026_GROUPS.map((group) => (
          <button
            key={group.id}
            onClick={() => onSelectGroup(group)}
            className="bg-navy-800 border border-navy-600 rounded-xl p-4 text-left hover:border-fifa-blue hover:bg-navy-700 transition-all group"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold tracking-widest text-fifa-blue uppercase">
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
                  <span className={`text-sm font-medium ${HOST_COLORS[team] ?? "text-slate-300"}`}>
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
