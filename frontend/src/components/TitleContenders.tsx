"use client";
import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import Link from "next/link";
import FlagIcon from "@/components/FlagIcon";
import { useSimulation } from "@/hooks/useSimulation";
import { reachProb } from "@/lib/types";
import type { TeamSimResult } from "@/lib/types";

type StageShorthand = { short: string; reach: (t: TeamSimResult) => number };

const STAGES: StageShorthand[] = [
  { short: "QF",    reach: (t) => reachProb(t, "qf") },
  { short: "SF",    reach: (t) => reachProb(t, "sf") },
  { short: "Final", reach: (t) => reachProb(t, "final") },
  { short: "Win",   reach: (t) => reachProb(t, "champion") },
];

/* ── Animated probability bar ── */
function Bar({ value, max, delay }: { value: number; max: number; delay: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <div ref={ref} className="flex-1 h-[2px] bg-white/[0.08] rounded-full overflow-hidden">
      <motion.div
        className="h-full bg-pitch-400"
        initial={{ width: 0 }}
        animate={inView ? { width: `${(value / max) * 100}%` } : {}}
        transition={{ duration: 1.1, delay, ease: [0.22, 1, 0.36, 1] }}
      />
    </div>
  );
}

/* ── Loading skeleton ── */
function LoadingSkeleton() {
  return (
    <section className="relative bg-navy-900 overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute inset-0" style={{
        background:
          "radial-gradient(ellipse at 15% 40%, rgba(34,160,82,0.10) 0%, transparent 52%)," +
          "radial-gradient(ellipse at 85% 75%, rgba(245,200,66,0.05) 0%, transparent 48%)",
      }} />
      <div className="relative max-w-7xl mx-auto px-8 md:px-14 py-24 space-y-4 animate-pulse">
        {/* Eyebrow */}
        <div className="h-3 w-64 rounded-full bg-white/[0.07]" />
        {/* Heading */}
        <div className="h-16 w-80 rounded bg-white/[0.06]" />
        <div className="h-16 w-52 rounded bg-white/[0.05]" />
        {/* Subtext */}
        <div className="h-4 w-96 rounded-full bg-white/[0.04] pt-2" />

        {/* Computing notice */}
        <div className="pt-6 pb-2">
          <p className="font-jb text-[11px] tracking-[0.16em] uppercase text-[rgba(240,236,226,0.3)] flex items-center gap-2.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-pitch-400 animate-pulse" />
            Computing 1,000 simulations · may take ~60 s on first load
          </p>
        </div>

        {/* Champion card placeholder */}
        <div className="h-52 rounded-[4px] bg-white/[0.04] border border-white/[0.06]" />

        {/* Row placeholders */}
        <div className="rounded-[4px] border border-white/[0.07] overflow-hidden">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="h-[68px] bg-white/[0.025] border-t border-white/[0.04] first:border-t-0" />
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── Offline / error fallback ── */
function OfflineState() {
  return (
    <section className="relative bg-navy-900 overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute inset-0" style={{
        background: "radial-gradient(ellipse at 15% 40%, rgba(34,160,82,0.08) 0%, transparent 52%)",
      }} />
      <div className="relative max-w-7xl mx-auto px-8 md:px-14 py-24">
        <p className="font-jb text-[11px] tracking-[0.18em] uppercase text-pitch-400 mb-4">
          ◆ Tournament Forecast
        </p>
        <h2 className="font-anton uppercase leading-[0.88] tracking-[-0.01em] text-[#f0ece2] mb-6 text-[56px] sm:text-[76px] md:text-[100px]">
          Who lifts<br />
          <span className="text-pitch-400">the cup?</span>
        </h2>
        <div className="inline-flex items-center gap-4 bg-white/[0.04] border border-white/[0.08] rounded-[4px] px-7 py-5">
          <div className="w-2 h-2 rounded-full bg-[rgba(240,236,226,0.2)]" />
          <div>
            <p className="text-[rgba(240,236,226,0.55)] text-sm leading-relaxed">
              Live odds unavailable — backend may be offline.
            </p>
            <Link href="/simulate" className="font-jb text-[12px] text-pitch-400 hover:text-pitch-300 transition-colors tracking-wide">
              Try the simulation page →
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── Main component ── */
export default function TitleContenders() {
  const { data, loading, error } = useSimulation();

  if (loading) return <LoadingSkeleton />;
  if (error || !data) return <OfflineState />;

  const sorted = [...data.teams].sort((a, b) => b.champion - a.champion);
  const champion = sorted[0];
  const contenders = sorted.slice(1, 8);

  return (
    <section className="relative bg-navy-900 overflow-hidden">
      {/* Atmospheric gradients */}
      <div aria-hidden className="pointer-events-none absolute inset-0" style={{
        background:
          "radial-gradient(ellipse at 15% 40%, rgba(34,160,82,0.14) 0%, transparent 52%)," +
          "radial-gradient(ellipse at 88% 72%, rgba(245,200,66,0.07) 0%, transparent 48%)",
      }} />
      {/* Vertical pitch stripes — matching hero */}
      <div aria-hidden className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{ background: "repeating-linear-gradient(90deg, transparent 0 80px, #fff 80px 81px)" }}
      />

      <div className="relative max-w-7xl mx-auto px-8 md:px-14 py-24">

        {/* Eyebrow */}
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="font-jb text-[11px] tracking-[0.18em] uppercase text-pitch-400 mb-4"
        >
          ◆ Tournament Forecast · {data.n_simulations.toLocaleString()} Monte Carlo Simulations
        </motion.p>

        {/* Heading */}
        <motion.h2
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.07 }}
          className="font-anton uppercase leading-[0.88] tracking-[-0.01em] text-[#f0ece2] mb-4 text-[56px] sm:text-[76px] md:text-[100px]"
        >
          Who lifts<br />
          <span className="text-pitch-400">the cup?</span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.14 }}
          className="text-[15px] leading-relaxed text-[rgba(240,236,226,0.5)] max-w-[480px] mb-14"
        >
          Predicted championship probability for all 48 nations, ranked by our
          ensemble ML model across {data.n_simulations.toLocaleString()} simulated tournaments.
        </motion.p>

        {/* ── #1 Champion card ── */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, delay: 0.2 }}
          className="relative overflow-hidden rounded-[4px] border border-white/[0.12] mb-2.5"
        >
          {/* Glow */}
          <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
            background:
              "radial-gradient(ellipse at 28% 50%, rgba(34,160,82,0.30) 0%, rgba(34,160,82,0.07) 42%, transparent 68%)",
          }} />
          {/* Diagonal texture */}
          <div aria-hidden className="absolute inset-0 pointer-events-none opacity-[0.045]" style={{
            background:
              "repeating-linear-gradient(-45deg, rgba(255,255,255,0.1) 0px, rgba(255,255,255,0.1) 1px, transparent 1px, transparent 28px)",
          }} />
          {/* "01" watermark */}
          <div aria-hidden className="absolute right-4 md:right-10 top-1/2 -translate-y-1/2 font-anton leading-none select-none pointer-events-none opacity-[0.07] text-pitch-400 text-[160px] md:text-[220px]">
            01
          </div>

          <div className="relative flex flex-col md:flex-row md:items-center gap-5 p-5 md:px-12 md:py-10">
            {/* Left: label · flag · name · stage breakdown */}
            <div className="flex flex-col gap-5 flex-1 min-w-0">
              <span className="inline-flex items-center gap-2.5 font-jb text-[10px] tracking-[0.18em] uppercase text-pitch-400">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-pitch-400 animate-pulse" />
                Predicted Champion · 2026
              </span>

              <div className="flex items-center gap-5">
                <FlagIcon
                  team={champion.team}
                  className="w-[80px] h-[58px] md:w-[96px] md:h-[70px] rounded-[3px] shadow-xl"
                />
                <h3 className="font-anton uppercase leading-none tracking-[-0.01em] text-[#f0ece2] text-[40px] md:text-[58px]">
                  {champion.team}
                </h3>
              </div>

              {/* Stage breakdown */}
              <div className="flex gap-6">
                {STAGES.map(({ short, reach }) => (
                  <div key={short} className="flex flex-col gap-1">
                    <span className="font-jb text-[10px] tracking-[0.1em] uppercase text-[rgba(240,236,226,0.3)]">
                      {short}
                    </span>
                    <span className="font-anton text-[22px] leading-none text-[rgba(240,236,226,0.78)]">
                      {(reach(champion) * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: mega percentage */}
            <div className="flex-shrink-0 flex flex-col items-start md:items-end md:pl-10">
              <div className="font-anton leading-none tabular-nums text-pitch-400 text-[80px] sm:text-[100px] md:text-[130px] xl:text-[152px]">
                {(champion.champion * 100).toFixed(1)}%
              </div>
              <span className="font-jb text-[10px] tracking-[0.14em] uppercase text-[rgba(240,236,226,0.3)] mt-1">
                Championship Probability
              </span>
            </div>
          </div>
        </motion.div>

        {/* ── Ranked contenders #2–8 ── */}
        <div className="rounded-[4px] border border-white/[0.08] overflow-hidden">
          {contenders.map((team, i) => (
            <motion.div
              key={team.team}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.45, delay: 0.32 + i * 0.065 }}
            >
              {i > 0 && <div className="border-t border-white/[0.05]" />}
              <div className="flex items-center gap-2.5 md:gap-6 px-4 md:px-8 py-[18px] hover:bg-white/[0.02] transition-colors">

                {/* Rank */}
                <span className="font-anton text-[20px] md:text-[30px] leading-none tabular-nums w-7 md:w-10 flex-shrink-0 text-[rgba(240,236,226,0.1)]">
                  {String(i + 2).padStart(2, "0")}
                </span>

                {/* Flag + name */}
                <div className="flex items-center gap-2.5 flex-shrink-0 w-[110px] md:w-[210px]">
                  <FlagIcon team={team.team} className="w-8 h-[22px] md:w-9 md:h-[26px] rounded-[2px]" />
                  <span className="font-semibold text-[13px] md:text-[14px] text-[rgba(240,236,226,0.88)] truncate">
                    {team.team}
                  </span>
                </div>

                {/* Probability bar + percentage */}
                <div className="flex-1 flex items-center gap-2.5 md:gap-4 min-w-0">
                  <Bar value={team.champion} max={champion.champion} delay={0.35 + i * 0.07} />
                  <span className="font-jb text-[12px] md:text-[13px] text-pitch-300 tabular-nums w-11 md:w-12 text-right flex-shrink-0">
                    {(team.champion * 100).toFixed(1)}%
                  </span>
                </div>

                {/* Stage chips — desktop only */}
                <div className="hidden lg:flex items-center gap-5 flex-shrink-0 pl-2">
                  {STAGES.slice(0, 3).map(({ short, reach }) => (
                    <div key={short} className="flex flex-col items-center gap-0.5 w-10">
                      <span className="font-jb text-[9px] uppercase tracking-[0.08em] text-[rgba(240,236,226,0.28)]">
                        {short}
                      </span>
                      <span className="font-jb text-[12px] tabular-nums text-[rgba(240,236,226,0.52)]">
                        {(reach(team) * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 1.0 }}
          className="flex items-center justify-between mt-6 pt-6 border-t border-white/[0.06]"
        >
          <p className="font-jb text-[11px] text-[rgba(240,236,226,0.22)] tracking-wide">
            {data.n_simulations.toLocaleString()} simulations ·{" "}
            {new Date(data.generated_at).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </p>
          <Link
            href="/simulate"
            className="font-anton text-[13px] tracking-[0.08em] uppercase text-[rgba(240,236,226,0.4)] hover:text-pitch-400 transition-colors"
          >
            All 48 nations →
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
