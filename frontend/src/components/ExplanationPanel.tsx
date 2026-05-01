"use client";
import { useState } from "react";
import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/20/solid";
import type { Explanation } from "@/lib/types";

interface Props {
  explanation: Explanation;
  homeTeam: string;
  awayTeam: string;
}

function StatRow({ label, home, away }: { label: string; home: string; away: string }) {
  return (
    <div className="grid grid-cols-3 gap-2 text-sm py-2 border-b border-slate-700/50">
      <span className="text-slate-400">{label}</span>
      <span className="text-center text-white font-mono">{home}</span>
      <span className="text-center text-white font-mono">{away}</span>
    </div>
  );
}

export default function ExplanationPanel({ explanation, homeTeam, awayTeam }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm font-semibold text-slate-400 uppercase tracking-wider hover:text-slate-200 transition-colors"
      >
        {open ? <ChevronUpIcon className="h-4 w-4" /> : <ChevronDownIcon className="h-4 w-4" />}
        Model Explanation
      </button>
      {open && (
        <div className="bg-navy-800 rounded-xl p-4 border border-slate-700">
          <div className="grid grid-cols-3 gap-2 text-xs font-bold uppercase tracking-wider text-slate-500 pb-2 border-b border-slate-700 mb-1">
            <span>Stat</span>
            <span className="text-center truncate">{homeTeam}</span>
            <span className="text-center truncate">{awayTeam}</span>
          </div>
          <StatRow label="Elo Rating" home={explanation.home_elo.toFixed(0)} away={explanation.away_elo.toFixed(0)} />
          <StatRow label="Form (PPG)" home={explanation.home_form.toFixed(2)} away={explanation.away_form.toFixed(2)} />
          <StatRow label="FIFA Rank" home={`#${explanation.home_rank}`} away={`#${explanation.away_rank}`} />
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div className="bg-navy-700 rounded-lg p-3">
              <div className="text-slate-400 text-xs">Elo Win Prob</div>
              <div className="text-white font-bold">{(explanation.elo_win_prob * 100).toFixed(1)}%</div>
            </div>
            <div className="bg-navy-700 rounded-lg p-3">
              <div className="text-slate-400 text-xs">Competition Weight</div>
              <div className="text-white font-bold">{explanation.competition_weight.toFixed(2)}</div>
            </div>
            <div className="bg-navy-700 rounded-lg p-3">
              <div className="text-slate-400 text-xs">Same Confederation</div>
              <div className="text-white font-bold">{explanation.is_same_confederation ? "Yes" : "No"}</div>
            </div>
            <div className="bg-navy-700 rounded-lg p-3">
              <div className="text-slate-400 text-xs">Elo Diff</div>
              <div className="text-white font-bold">{explanation.elo_diff > 0 ? "+" : ""}{explanation.elo_diff.toFixed(0)}</div>
            </div>
          </div>
          {explanation.data_note && (
            <p className="mt-3 text-xs text-slate-500 italic">{explanation.data_note}</p>
          )}
        </div>
      )}
    </div>
  );
}
