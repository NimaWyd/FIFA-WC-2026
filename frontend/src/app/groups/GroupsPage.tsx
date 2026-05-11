"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { WC2026_GROUPS, WCGroup, WCMatch } from "@/lib/wc2026Groups";
import GroupBracket from "@/components/GroupBracket";
import GroupView from "@/components/GroupView";

const GROUP_IDS = WC2026_GROUPS.map((g) => g.id);

export default function GroupsPage() {
  const router = useRouter();
  const [selectedGroup, setSelectedGroup] = useState<WCGroup | null>(null);

  function handleMatchPredict(match: WCMatch) {
    const params = new URLSearchParams({
      home: match.home,
      away: match.away,
      date: match.date,
      stage: "Group Stage",
    });
    router.push(`/predict?${params.toString()}`);
  }

  return (
    <main className="min-h-screen bg-navy-900 overflow-x-hidden">
      {/* ── Hero ────────────────────────────────────────────────── */}
      <div className="relative overflow-hidden">
        {/* Pitch-circle backdrop rings */}
        <div className="pointer-events-none select-none absolute inset-0">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full border border-white/[0.025]" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[480px] h-[480px] rounded-full border border-white/[0.025]" />
        </div>

        {/* Blue glow bloom */}
        <div className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-[520px] h-28 bg-fifa-blue/15 blur-[72px] rounded-full" />

        <div className="relative max-w-5xl mx-auto px-4 pt-14 pb-10 flex flex-col items-center text-center gap-3">
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-[11px] font-bold tracking-[0.35em] text-fifa-blue uppercase"
          >
            FIFA World Cup 2026
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.55, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="font-anton text-[72px] sm:text-[100px] leading-none tracking-wide text-white uppercase"
          >
            Group Stage
          </motion.h1>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35, duration: 0.5 }}
            className="flex items-center gap-3 mt-1"
          >
            {["12 Groups", "48 Teams", "June 11 – July 2, 2026"].map((s, i) => (
              <span key={s} className="flex items-center gap-3">
                {i > 0 && <span className="w-1 h-1 rounded-full bg-navy-600" />}
                <span className="text-xs tracking-widest text-slate-500 uppercase">{s}</span>
              </span>
            ))}
          </motion.div>
        </div>

        {/* ── Group selector strip ─────────────────────────────── */}
        <div className="border-t border-navy-600 bg-navy-800/60 backdrop-blur-md">
          <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-1.5 flex-wrap">
            {GROUP_IDS.map((id, i) => (
              <motion.button
                key={id}
                initial={{ opacity: 0, scale: 0.75 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 + i * 0.035, duration: 0.28, ease: "backOut" }}
                onClick={() =>
                  setSelectedGroup(WC2026_GROUPS.find((g) => g.id === id) ?? null)
                }
                className={`relative w-10 h-10 rounded-lg text-sm font-bold transition-all duration-200 ${
                  selectedGroup?.id === id
                    ? "bg-fifa-blue text-white shadow-[0_0_18px_rgba(26,63,255,0.65)] scale-105"
                    : "bg-navy-900 border border-navy-600 text-slate-500 hover:text-white hover:border-fifa-blue/50 hover:shadow-[0_0_10px_rgba(26,63,255,0.25)]"
                }`}
              >
                {id}
              </motion.button>
            ))}

            <AnimatePresence>
              {selectedGroup && (
                <motion.button
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => setSelectedGroup(null)}
                  className="ml-2 px-3 h-10 rounded-lg text-xs text-slate-500 border border-navy-600 hover:text-white hover:border-slate-500 transition-colors"
                >
                  ← All Groups
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-4 py-8">
        <AnimatePresence mode="wait">
          {selectedGroup ? (
            <motion.div
              key={selectedGroup.id}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.28, ease: "easeOut" }}
            >
              <GroupView
                group={selectedGroup}
                onBack={() => setSelectedGroup(null)}
                onPredict={handleMatchPredict}
              />
            </motion.div>
          ) : (
            <motion.div
              key="bracket"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.28, ease: "easeOut" }}
            >
              <GroupBracket onSelectGroup={setSelectedGroup} showHeader={false} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
