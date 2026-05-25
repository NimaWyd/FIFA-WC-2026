"use client";
import Link from "next/link";
import TrophyEmbed from "./TrophyEmbed";

const OPENING_MATCHES = [
  { home: "MEX", away: "RSA", date: "JUN 11", venue: "Mexico City", group: "GROUP A" },
  { home: "CAN", away: "BIH", date: "JUN 12", venue: "Toronto", group: "GROUP B" },
  { home: "QAT", away: "SUI", date: "JUN 13", venue: "San Francisco", group: "GROUP B" },
] as const;

const STATS = [
  ["48", "Nations"],
  ["104", "Matches"],
  ["16", "Cities"],
  ["39", "Days"],
] as const;

export default function LandingHero() {
  return (
    <section className="relative min-h-[90vh] sm:min-h-screen bg-navy-900 overflow-hidden text-[#f0ece2]">
      {/* Radial gradients */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 30% 60%, rgba(34,160,82,0.28) 0%, transparent 52%), radial-gradient(ellipse at 82% 18%, rgba(245,200,66,0.12) 0%, transparent 58%)",
        }}
      />
      {/* Pitch stripes */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.05]"
        style={{ background: "repeating-linear-gradient(90deg, transparent 0 80px, #fff 80px 81px)" }}
      />

      {/* ── Hero grid ── */}
      <div className="relative grid grid-cols-1 md:grid-cols-[1.1fr_1fr] px-8 md:px-14 pt-8 md:pt-10 pb-52 md:pb-60 animate-fade-in">
        {/* Left: text + CTAs + stats */}
        <div className="pt-4 md:pt-9">
          <p className="font-jb text-[12px] tracking-[0.16em] uppercase text-pitch-400">
            ◆ World Cup Predictor · USA · MEX · CAN
          </p>

          <h1 className="font-anton uppercase leading-[0.86] tracking-[-0.01em] mt-3 text-[72px] sm:text-[96px] md:text-[120px] lg:text-[148px] xl:text-[168px]">
            <span className="block">Call</span>
            <span className="block text-pitch-400">every</span>
            <span className="block">match.</span>
          </h1>

          {/* Mobile trophy — visible only below md breakpoint */}
          <div className="md:hidden relative h-[280px] mt-4 -mx-2 overflow-hidden">
            <div className="animate-float w-full h-full">
              <TrophyEmbed className="w-full h-full" />
            </div>
          </div>

          <p className="max-w-[480px] text-[16px] leading-[1.55] text-[rgba(240,236,226,0.68)] mt-3 md:mt-7">
            Predict outcomes. Simulate the bracket. Discover who the AI thinks wins FIFA World Cup 2026.
          </p>

          <div className="flex flex-wrap gap-3 mt-7 md:mt-8">
            <Link
              href="/predict"
              className="font-anton text-[15px] tracking-[0.09em] px-7 py-4 bg-pitch-400 text-navy-900 rounded-[2px] hover:bg-pitch-300 transition-colors"
            >
              PREDICT A MATCH →
            </Link>
            <Link
              href="/groups"
              className="font-anton text-[15px] tracking-[0.09em] px-7 py-4 bg-transparent text-[#f0ece2] border border-white/[0.18] rounded-[2px] hover:border-white/40 transition-colors"
            >
              VIEW GROUPS
            </Link>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-6 sm:gap-y-0 mt-12 md:mt-14 pt-[22px] border-t border-white/[0.08]">
            {STATS.map(([n, l]) => (
              <div key={l}>
                <div className="font-anton text-[36px] md:text-[44px] leading-none">{n}</div>
                <div className="text-[11px] uppercase tracking-[0.08em] text-[rgba(240,236,226,0.5)] mt-1.5">
                  {l}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: 3D trophy */}
        <div className="hidden md:block relative h-[580px] lg:h-[640px] -mt-5">
          <div className="animate-float w-full h-full">
            <TrophyEmbed className="w-full h-full" />
          </div>
          <span className="absolute top-0 right-0 font-jb text-[11px] tracking-[0.14em] text-[rgba(240,236,226,0.35)]">
            EDITION · XXIII
          </span>
          <span className="absolute bottom-2 right-0 font-jb text-[11px] tracking-[0.14em] text-[rgba(240,236,226,0.35)]">
            JUN 11 → JUL 19, 2026
          </span>
        </div>
      </div>

      {/* ── Fixture strip ── */}
      <div className="absolute bottom-6 left-8 right-8 md:left-14 md:right-14 grid grid-cols-[auto_1fr] gap-6 md:gap-8 items-start">
        <div className="pt-1 flex-shrink-0">
          <div className="font-jb text-[11px] tracking-[0.14em] text-[rgba(240,236,226,0.4)] uppercase mb-2.5">
            Upcoming
          </div>
          <div className="font-anton text-[30px] md:text-[38px] leading-[1.05]">
            GROUP
            <br />
            STAGE
          </div>
        </div>
        <div className="flex gap-3 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none]">
          {OPENING_MATCHES.map((m) => (
            <div
              key={m.home}
              className="flex-shrink-0 bg-white/[0.04] border border-white/[0.08] rounded-[4px] px-[18px] py-4 min-w-[200px] flex flex-col gap-3.5"
            >
              <div className="flex justify-between items-center">
                <span className="font-jb text-[10px] tracking-[0.12em] text-[rgba(240,236,226,0.5)]">
                  {m.group}
                </span>
                <span className="font-jb text-[10px] tracking-[0.12em] text-[rgba(240,236,226,0.5)]">
                  {m.date}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <div className="flex flex-col gap-1.5">
                  <span className="font-anton text-[26px] leading-none">{m.home}</span>
                  <span className="font-anton text-[26px] leading-none text-[rgba(240,236,226,0.65)]">
                    {m.away}
                  </span>
                </div>
                <span className="font-jb text-[11px] text-[rgba(240,236,226,0.4)] text-right leading-snug">
                  {m.venue}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
