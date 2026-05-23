"use client";
import { useState } from "react";
import { ChevronDownIcon } from "@heroicons/react/20/solid";
import { motion, AnimatePresence } from "framer-motion";
import type { Explanation } from "@/lib/types";
import { displayName } from "@/lib/utils";

interface Props {
  explanation: Explanation;
  homeTeam: string;
  awayTeam: string;
}

function StatRow({ label, home, away }: { label: string; home: string; away: string }) {
  return (
    <div className="grid grid-cols-3 gap-2 py-2.5 border-b border-navy-600/60 last:border-0">
      <span className="text-slate-500 text-[11px]">{label}</span>
      <span className="text-center text-white font-mono font-bold text-[11px]">{home}</span>
      <span className="text-center text-white font-mono font-bold text-[11px]">{away}</span>
    </div>
  );
}

export default function ExplanationPanel({ explanation, homeTeam, awayTeam }: Props) {
  const [open, setOpen] = useState(false);

  const homeDisplay = displayName(homeTeam);
  const awayDisplay = displayName(awayTeam);

  return (
    <div className="flex flex-col gap-0">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center justify-between w-full text-left group py-0.5"
      >
        <span className="text-[11px] font-bold tracking-[0.22em] text-slate-500 uppercase group-hover:text-slate-300 transition-colors">
          Model Explanation
        </span>
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDownIcon className="h-4 w-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
        </motion.div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="pt-4">
              <div className="bg-navy-900/60 rounded-xl p-4 border border-navy-600/60">
                <div className="grid grid-cols-3 gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-600 pb-2.5 border-b border-navy-600/60 mb-1">
                  <span>Stat</span>
                  <span className="text-center truncate">{homeDisplay}</span>
                  <span className="text-center truncate">{awayDisplay}</span>
                </div>
                <StatRow label="Elo Rating" home={explanation.home_elo.toFixed(0)} away={explanation.away_elo.toFixed(0)} />
                <StatRow label="Form (PPG)" home={explanation.home_form.toFixed(2)} away={explanation.away_form.toFixed(2)} />
                <StatRow label="FIFA Rank" home={`#${explanation.home_rank}`} away={`#${explanation.away_rank}`} />
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <div className="bg-navy-800 rounded-lg p-3 border border-navy-600/60">
                    <div className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Elo Win Prob</div>
                    <div className="text-white font-bold font-mono text-sm">{(explanation.elo_win_prob * 100).toFixed(1)}%</div>
                  </div>
                  <div className="bg-navy-800 rounded-lg p-3 border border-navy-600/60">
                    <div className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Comp. Weight</div>
                    <div className="text-white font-bold font-mono text-sm">{explanation.competition_weight.toFixed(2)}</div>
                  </div>
                  <div className="bg-navy-800 rounded-lg p-3 border border-navy-600/60">
                    <div className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Same Confed.</div>
                    <div className="text-white font-bold text-sm">{explanation.is_same_confederation ? "Yes" : "No"}</div>
                  </div>
                  <div className="bg-navy-800 rounded-lg p-3 border border-navy-600/60">
                    <div className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Elo Diff</div>
                    <div className="text-white font-bold font-mono text-sm">{explanation.elo_diff > 0 ? "+" : ""}{explanation.elo_diff.toFixed(0)}</div>
                  </div>
                </div>
                {explanation.data_note && (
                  <p className="mt-3 text-xs text-slate-600 italic">{explanation.data_note}</p>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
