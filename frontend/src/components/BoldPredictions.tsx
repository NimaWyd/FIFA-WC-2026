"use client";

import { useMemo } from "react";
import FlagIcon from "@/components/FlagIcon";
import { useSimulation } from "@/hooks/useSimulation";
import { WC2026_GROUPS } from "@/lib/wc2026Groups";
import { reachProb } from "@/lib/types";
import type { TeamSimResult } from "@/lib/types";

const display = (name: string) => (name === "United States" ? "USA" : name);

/* ── Card data ─────────────────────────────────────────────── */
type PredCard = {
  id: string;
  tag: string;
  tagColor: string;
  borderColor: string;
  glowColor: string;
  teams: string[];
  headline: string;
  bigStat: string;
  statLabel: string;
  sub: string;
};

function buildCards(teams: TeamSimResult[]): PredCard[] {
  const byTeam = Object.fromEntries(teams.map((t) => [t.team, t]));
  const sorted = [...teams].sort((a, b) => b.champion - a.champion);
  const cards: PredCard[] = [];

  /* 1 — Title favourite */
  const fav = sorted[0];
  if (fav) {
    cards.push({
      id: "favourite",
      tag: "Title Favourite",
      tagColor: "text-gold-500",
      borderColor: "rgba(245,200,66,0.22)",
      glowColor: "rgba(245,200,66,0.10)",
      teams: [fav.team],
      headline: `${display(fav.team)} lead the field`,
      bigStat: `${(fav.champion * 100).toFixed(1)}%`,
      statLabel: "to lift the trophy",
      sub: `${(reachProb(fav, "final") * 100).toFixed(0)}% reach Final · ${(reachProb(fav, "sf") * 100).toFixed(0)}% reach SF`,
    });
  }

  /* 2 — Group of Death
   * The most competitive group: all 4 teams are close in strength, so even
   * the weakest side has a realistic chance to advance. We measure this by
   * the standard deviation of each team's probability of reaching the R16
   * (= 1 - group_exit). The group with the LOWEST std dev has the smallest
   * gap between its best and worst team — the truest "Group of Death".
   */
  const deathGroup = WC2026_GROUPS.map((g) => {
    const gt = g.teams.map((n) => byTeam[n]).filter(Boolean) as TeamSimResult[];
    const advProbs = gt.map((t) => reachProb(t, "r16"));
    const mean = advProbs.reduce((s, p) => s + p, 0) / advProbs.length;
    const stdDev = Math.sqrt(
      advProbs.reduce((s, p) => s + (p - mean) ** 2, 0) / advProbs.length
    );
    return { g, gt, stdDev };
  }).sort((a, b) => a.stdDev - b.stdDev)[0];

  if (deathGroup) {
    const top2 = [...deathGroup.gt]
      .sort((a, b) => b.champion - a.champion)
      .slice(0, 2);
    cards.push({
      id: "group_of_death",
      tag: "Group of Death",
      tagColor: "text-[rgba(255,110,70,0.95)]",
      borderColor: "rgba(255,110,70,0.18)",
      glowColor: "rgba(255,110,70,0.07)",
      teams: deathGroup.g.teams.slice(0, 4),
      headline: `Group ${deathGroup.g.id} is loaded`,
      bigStat: `GROUP ${deathGroup.g.id}`,
      statLabel: "the toughest draw in the tournament",
      sub: top2.map((t) => `${display(t.team)} ${(t.champion * 100).toFixed(1)}%`).join("  ·  "),
    });
  }

  /* 3 — Dark horse (outside top 8, highest SF reach odds) */
  const darkHorse = [...sorted.slice(8)].sort((a, b) => reachProb(b, "sf") - reachProb(a, "sf"))[0];
  if (darkHorse) {
    cards.push({
      id: "dark_horse",
      tag: "Dark Horse",
      tagColor: "text-pitch-400",
      borderColor: "rgba(34,160,82,0.22)",
      glowColor: "rgba(34,160,82,0.08)",
      teams: [darkHorse.team],
      headline: `Don't sleep on ${display(darkHorse.team)}`,
      bigStat: `${(reachProb(darkHorse, "sf") * 100).toFixed(0)}%`,
      statLabel: "chance to reach the semis",
      sub: `${(reachProb(darkHorse, "qf") * 100).toFixed(0)}% reach QF · ${(darkHorse.champion * 100).toFixed(1)}% to win it all`,
    });
  }

  /* 4 — Shock exit (top-12 team with highest group_exit%) */
  const shockTeam = [...sorted.slice(0, 12)].sort((a, b) => b.group_exit - a.group_exit)[0];
  if (shockTeam && shockTeam.group_exit > 0.20) {
    cards.push({
      id: "shock_exit",
      tag: "Shock Alert",
      tagColor: "text-[rgba(255,190,60,0.95)]",
      borderColor: "rgba(255,190,60,0.20)",
      glowColor: "rgba(255,190,60,0.07)",
      teams: [shockTeam.team],
      headline: `${display(shockTeam.team)} could crash out early`,
      bigStat: `${(shockTeam.group_exit * 100).toFixed(0)}%`,
      statLabel: "chance of a group-stage exit",
      sub: `Group ${shockTeam.group}  ·  only ${(reachProb(shockTeam, "qf") * 100).toFixed(0)}% to reach QF`,
    });
  }

  /* 5 — Title race: the two teams most likely to reach the final */
  const byFinal = [...teams].sort((a, b) => reachProb(b, "final") - reachProb(a, "final"));
  const [f1, f2] = byFinal;
  if (f1 && f2) {
    cards.push({
      id: "title_race",
      tag: "Title Race",
      tagColor: "text-[rgba(240,236,226,0.65)]",
      borderColor: "rgba(255,255,255,0.10)",
      glowColor: "rgba(255,255,255,0.025)",
      teams: [f1.team, f2.team],
      headline: `${display(f1.team)} vs ${display(f2.team)}`,
      bigStat: `${(f1.champion * 100).toFixed(1)}% — ${(f2.champion * 100).toFixed(1)}%`,
      statLabel: "to win the World Cup",
      sub: `${display(f1.team)} ${(reachProb(f1, "final") * 100).toFixed(0)}% reach Final  ·  ${display(f2.team)} ${(reachProb(f2, "final") * 100).toFixed(0)}% reach Final`,
    });
  }

  return cards;
}

/* ── Individual card ───────────────────────────────────────── */
function PredCard({ card }: { card: PredCard }) {
  return (
    <div
      className="flex-shrink-0 w-[270px] flex flex-col gap-4 rounded-[4px] px-6 py-5"
      style={{
        background: `radial-gradient(ellipse at 30% 0%, ${card.glowColor} 0%, transparent 65%), rgba(255,255,255,0.03)`,
        border: `1px solid ${card.borderColor}`,
      }}
    >
      <span className={`font-jb text-[10px] tracking-[0.16em] uppercase ${card.tagColor}`}>
        ◆ {card.tag}
      </span>

      <div className="flex gap-2.5 items-center">
        {card.teams.slice(0, 4).map((team) => (
          <FlagIcon
            key={team}
            team={team}
            className={
              card.teams.length === 1
                ? "w-14 h-[40px] rounded-[3px] shadow-lg"
                : card.teams.length === 2
                ? "w-10 h-[29px] rounded-[2px] shadow-md"
                : "w-8 h-[22px] rounded-[2px]"
            }
          />
        ))}
      </div>

      <p className="font-jb text-[11px] text-[rgba(240,236,226,0.5)] leading-snug">
        {card.headline}
      </p>

      <div className="mt-auto">
        <div className="font-anton text-[30px] leading-none text-[#f0ece2] tracking-[-0.01em]">
          {card.bigStat}
        </div>
        <div className="font-jb text-[10px] uppercase tracking-[0.1em] text-[rgba(240,236,226,0.32)] mt-1.5">
          {card.statLabel}
        </div>
      </div>

      <div className="pt-3 border-t border-white/[0.06]">
        <p className="font-jb text-[10px] text-[rgba(240,236,226,0.25)] leading-relaxed">
          {card.sub}
        </p>
      </div>
    </div>
  );
}

/* ── Skeleton ──────────────────────────────────────────────── */
function Skeleton() {
  return (
    <div className="flex gap-4 px-8 md:px-14">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex-shrink-0 w-[270px] h-[210px] rounded-[4px] bg-white/[0.04] border border-white/[0.07] animate-pulse"
        />
      ))}
    </div>
  );
}

/* ── Main export ───────────────────────────────────────────── */
export default function BoldPredictions() {
  const { data, loading, error } = useSimulation();

  const cards = useMemo(() => (data ? buildCards(data.teams) : []), [data]);

  if (error || (!loading && cards.length === 0)) return null;

  return (
    <section className="relative bg-navy-900 border-t border-white/[0.05] overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 20% 60%, rgba(34,160,82,0.05) 0%, transparent 50%)",
        }}
      />

      <div className="relative py-14 md:py-16">
        {/* Header — constrained */}
        <div className="max-w-7xl mx-auto px-8 md:px-14 mb-8 flex items-end justify-between">
          <div>
            <p className="font-jb text-[11px] tracking-[0.18em] uppercase text-pitch-400 mb-2">
              ◆ Bold Predictions
            </p>
            <h2 className="font-anton uppercase text-[#f0ece2] text-[32px] md:text-[42px] leading-[0.9] tracking-[-0.01em]">
              What the model<br />
              <span className="text-pitch-400">is calling</span>
            </h2>
          </div>
          {data && (
            <p className="hidden md:block font-jb text-[10px] text-[rgba(240,236,226,0.2)] tracking-wide text-right">
              {data.n_simulations.toLocaleString()} simulations
            </p>
          )}
        </div>

        {/* Scrolling strip — full width */}
        {loading ? (
          <Skeleton />
        ) : (
          <div
            className="relative overflow-hidden"
            style={{
              maskImage:
                "linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%)",
              WebkitMaskImage:
                "linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%)",
            }}
          >
            {/* Duplicate cards for seamless loop */}
            <div className="flex gap-4 animate-marquee w-max">
              {[...cards, ...cards].map((card, i) => (
                <PredCard key={`${card.id}-${i}`} card={card} />
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
