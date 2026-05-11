"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";

interface Props {
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  compact?: boolean;
}

function teamLabel(name: string) {
  return name === "United States" ? "USA" : name;
}

const STEP_MS = 350;
const START_DELAY_MS = 400;

function AnimatedGoals({ target }: { target: number }) {
  const [display, setDisplay] = useState<number | null>(null);

  useEffect(() => {
    setDisplay(null);
    let current = 0;
    // Brief pause before counting so the card appears first
    const startId = setTimeout(() => {
      setDisplay(0);
      if (target === 0) return;
      const id = setInterval(() => {
        current += 1;
        setDisplay(current);
        if (current >= target) clearInterval(id);
      }, STEP_MS);
      return () => clearInterval(id);
    }, START_DELAY_MS);
    return () => clearTimeout(startId);
  }, [target]);

  // Blank while the delay plays out
  if (display === null) {
    return (
      <span className="text-5xl font-black tabular-nums text-transparent select-none">
        {target}
      </span>
    );
  }

  return (
    <motion.span
      key={display}
      initial={{ scale: 2, opacity: 0, y: -16 }}
      animate={{ scale: 1, opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 18 }}
      className="text-5xl font-black tabular-nums bg-gradient-to-br from-white to-gold-500 bg-clip-text text-transparent"
    >
      {display}
    </motion.span>
  );
}

export default function MatchScoreboard({ homeTeam, awayTeam, homeGoals, awayGoals, compact = false }: Props) {
  if (compact) {
    return (
      <div className="flex items-center gap-1 bg-navy-700 rounded-lg px-2.5 py-1 border border-gold-500/40 flex-shrink-0">
        <span className="text-sm font-bold text-gold-500 w-4 text-center tabular-nums">{homeGoals}</span>
        <span className="text-slate-500 text-xs">–</span>
        <span className="text-sm font-bold text-gold-500 w-4 text-center tabular-nums">{awayGoals}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Predicted Score</h3>
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 flex flex-col items-center gap-2">
          <FlagIcon team={homeTeam} className="w-16 h-12 rounded" />
          <span className="text-sm font-semibold text-white text-center">{teamLabel(homeTeam)}</span>
        </div>
        <div className="flex items-center gap-3 px-8 py-4 bg-navy-700 rounded-2xl border border-gold-500/40">
          <AnimatedGoals target={homeGoals} />
          <span className="text-3xl text-slate-500 font-light">–</span>
          <AnimatedGoals target={awayGoals} />
        </div>
        <div className="flex-1 flex flex-col items-center gap-2">
          <FlagIcon team={awayTeam} className="w-16 h-12 rounded" />
          <span className="text-sm font-semibold text-white text-center">{teamLabel(awayTeam)}</span>
        </div>
      </div>
    </div>
  );
}
