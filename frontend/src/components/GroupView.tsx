"use client";
import { ArrowLeftIcon, ChevronRightIcon } from "@heroicons/react/24/solid";
import { WCGroup, WCMatch } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";

interface Props {
  group: WCGroup;
  onBack: () => void;
  onPredict: (match: WCMatch) => void;
}

function formatDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const MATCHDAY_LABELS = ["Matchday 1", "Matchday 1", "Matchday 2", "Matchday 2", "Matchday 3", "Matchday 3"];

export default function GroupView({ group, onBack, onPredict }: Props) {
  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-1.5 rounded-lg bg-[#0d1428] border border-slate-800 text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
        >
          <ArrowLeftIcon className="h-4 w-4" />
        </button>
        <div>
          <h2 className="text-lg font-bold text-white">Group {group.id}</h2>
          <p className="text-xs text-slate-500">{group.teams.join(" · ")}</p>
        </div>
      </div>

      {/* Teams strip */}
      <div className="bg-[#0d1428] border border-slate-800 rounded-xl p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {group.teams.map((team) => (
            <div key={team} className="flex flex-col items-center gap-1.5">
              <FlagIcon team={team} className="w-10 h-7 rounded" />
              <span className="text-xs font-medium text-slate-300 text-center leading-tight">
                {team === "United States" ? "USA" : team}
              </span>
              {["Mexico", "United States", "Canada"].includes(team) && (
                <span className="text-[10px] text-[#d4af37]">Host</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Match cards */}
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Fixtures</h3>
        {group.matches.map((match, idx) => (
          <div
            key={idx}
            className="bg-[#0d1428] border border-slate-800 rounded-xl p-4 flex items-center gap-3"
          >
            {/* Matchday label */}
            <div className="hidden sm:block w-20 flex-shrink-0">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                {MATCHDAY_LABELS[idx]}
              </span>
              <div className="text-xs text-slate-400 mt-0.5">{formatDate(match.date)}</div>
              <div className="text-[10px] text-slate-600 mt-0.5">{match.venue}</div>
            </div>

            {/* Teams */}
            <div className="flex-1 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 flex-1">
                <FlagIcon team={match.home} className="w-7 h-5 rounded-sm flex-shrink-0" />
                <span className="text-sm font-semibold text-white truncate">
                  {match.home === "United States" ? "USA" : match.home}
                </span>
              </div>

              <div className="flex flex-col items-center gap-0.5 flex-shrink-0 px-2">
                <span className="text-xs font-bold text-slate-500">VS</span>
                {/* mobile date */}
                <span className="sm:hidden text-[10px] text-slate-600">{formatDate(match.date)}</span>
              </div>

              <div className="flex items-center gap-2 flex-1 justify-end">
                <span className="text-sm font-semibold text-white truncate text-right">
                  {match.away === "United States" ? "USA" : match.away}
                </span>
                <FlagIcon team={match.away} className="w-7 h-5 rounded-sm flex-shrink-0" />
              </div>
            </div>

            {/* Predict button */}
            <button
              onClick={() => onPredict(match)}
              className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[#d4af37]/10 border border-[#d4af37]/30 text-[#d4af37] text-xs font-semibold hover:bg-[#d4af37]/20 hover:border-[#d4af37]/60 transition-all"
            >
              Predict
              <ChevronRightIcon className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
