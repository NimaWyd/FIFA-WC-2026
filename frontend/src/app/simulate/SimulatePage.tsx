"use client";

import { useState, useRef, useLayoutEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";
import { useBracket } from "@/hooks/useBracket";
import { useSimulation } from "@/hooks/useSimulation";
import type { BracketMatch, BracketRound, TeamSimResult } from "@/lib/types";

// ─── Round tab labels ─────────────────────────────────────────────────────────
const ROUND_LABELS: Record<string, string> = {
  "Round of 32":      "R32",
  "Round of 16":      "R16",
  "Quarter-Final":    "QF",
  "Semi-Final":       "SF",
  "3rd Place Playoff":"3rd Place",
  "Final":            "Final",
};

// ═══════════════════════════════════════════════════════════════════════════════
// Visual bracket diagram (R16 → QF → SF → Final)
// Only rendered on md+ screens (too dense on mobile).
// ═══════════════════════════════════════════════════════════════════════════════

const D_ROW_H    = 35
const D_CARD_H   = D_ROW_H * 2 + 2       // 72px — 2 rows + 2px divider
const D_CARD_W   = 175
const D_FINAL_W  = 192
const D_GAP      = 14                    // vertical gap between stacked cards
const D_SVG_W    = 28
const D_HLINE_W  = 16
const D_HDR_H    = 26

const D_BRACKET_H = 4 * D_CARD_H + 3 * D_GAP   // 330

// Vertical centres for each round (left side; right mirrors by symmetry)
const D_R16_Y = [0, 1, 2, 3].map(i => i * (D_CARD_H + D_GAP) + D_CARD_H / 2)
// ≈ [36, 122, 208, 294]
const D_QF_Y = [
  (D_R16_Y[0] + D_R16_Y[1]) / 2,   // ≈ 79
  (D_R16_Y[2] + D_R16_Y[3]) / 2,   // ≈ 251
]
const D_SF_Y = D_BRACKET_H / 2      // 165

// Total natural width = two sides × (R16 + SVG + QF + SVG + SF + HLine) + Final + padding
const D_NATURAL_W =
  (D_CARD_W + D_SVG_W + D_CARD_W + D_SVG_W + D_CARD_W + D_HLINE_W) * 2 +
  D_FINAL_W + 48
// = 597 × 2 + 192 + 48 = 1434

const D_NATURAL_H = D_HDR_H + D_BRACKET_H + 16  // 372

// ── Label above each column ───────────────────────────────────────────────────
function DLabel({ text, icon }: { text: string; icon: string }) {
  return (
    <div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-[0.14em] text-slate-600">
      <span>{icon}</span>
      <span>{text}</span>
    </div>
  );
}

// ── Team row inside a diagram card ────────────────────────────────────────────
function DRow({ team, prob, isWinner, large = false }: {
  team: string; prob: number; isWinner: boolean; large?: boolean;
}) {
  const pct = (prob * 100).toFixed(0);
  return (
    <div
      className={`relative flex items-center gap-1.5 px-2 transition-colors ${isWinner ? "bg-gold-500/[0.06]" : ""}`}
      style={{ height: D_ROW_H }}
    >
      {isWinner && (
        <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gold-400 rounded-r-sm" />
      )}
      <FlagIcon
        team={team}
        className={large ? "w-6 h-[16px] rounded-sm shrink-0" : "w-[18px] h-[12px] rounded-sm shrink-0"}
      />
      <span className={`flex-1 truncate leading-none font-medium ${large ? "text-[11.5px]" : "text-[10px]"} ${isWinner ? "text-white" : "text-slate-500"}`}>
        {team}
      </span>
      <span className={`font-bold tabular-nums ${large ? "text-[12px]" : "text-[10px]"} ${isWinner ? "text-gold-400" : "text-slate-600"}`}>
        {pct}%
      </span>
    </div>
  );
}

// ── Match card inside the diagram ─────────────────────────────────────────────
function DCard({ match, isFinal = false, fromLeft = true, delay = 0 }: {
  match: BracketMatch; isFinal?: boolean; fromLeft?: boolean; delay?: number;
}) {
  const w = isFinal ? D_FINAL_W : D_CARD_W;
  const transition = isFinal
    ? { duration: 0.4, delay, type: "spring" as const, stiffness: 220, damping: 22 }
    : { duration: 0.32, delay, ease: "easeOut" as const };

  return (
    <motion.div
      initial={{
        opacity: 0,
        x:     isFinal ? 0            : (fromLeft ? -12 : 12),
        y:     isFinal ? 10           : 0,
        scale: isFinal ? 0.93         : 1,
      }}
      animate={{ opacity: 1, x: 0, y: 0, scale: 1 }}
      transition={transition}
      whileHover={{ scale: 1.014, transition: { duration: 0.15 } }}
      className="overflow-hidden rounded-lg border border-navy-600/60 bg-navy-800 shrink-0 cursor-default"
      style={{
        width:  w,
        height: D_CARD_H,
        ...(isFinal ? {
          background: "linear-gradient(135deg, rgba(197,130,39,0.10) 0%, rgba(21,24,41,1) 70%)",
          border:     "1px solid rgba(245,200,66,0.26)",
          boxShadow:  "0 0 22px rgba(245,200,66,0.06), inset 0 1px 0 rgba(245,200,66,0.08)",
        } : {}),
      }}
    >
      <DRow team={match.team1} prob={match.team1_win_prob} isWinner={match.predicted_winner === match.team1} large={isFinal} />
      <div className="h-px bg-navy-600/35 mx-1.5" />
      <DRow team={match.team2} prob={match.team2_win_prob} isWinner={match.predicted_winner === match.team2} large={isFinal} />
    </motion.div>
  );
}

// ── Animated SVG connector (pathLength draw-on) ───────────────────────────────
function DConnector({ from, to, height, width = D_SVG_W, delay = 0 }: {
  from: number[]; to: number[]; height: number; width?: number; delay?: number;
}) {
  const mx = width / 2;
  const paths: string[] = [];

  if (from.length >= to.length) {
    const ratio = from.length / to.length;
    to.forEach((toY, ti) =>
      from.slice(ti * ratio, (ti + 1) * ratio).forEach(fromY =>
        paths.push(`M 0,${fromY} L ${mx},${fromY} L ${mx},${toY} L ${width},${toY}`)
      )
    );
  } else {
    const ratio = to.length / from.length;
    from.forEach((fromY, fi) =>
      to.slice(fi * ratio, (fi + 1) * ratio).forEach(toY =>
        paths.push(`M 0,${fromY} L ${mx},${fromY} L ${mx},${toY} L ${width},${toY}`)
      )
    );
  }

  return (
    <svg width={width} height={height} className="shrink-0" style={{ marginTop: D_HDR_H }}>
      {paths.map((d, i) => (
        <motion.path
          key={d}
          d={d}
          fill="none"
          stroke="rgba(100,116,139,0.5)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{
            pathLength: { duration: 0.38, delay: delay + i * 0.03, ease: "easeInOut" },
            opacity:    { duration: 0.12, delay },
          }}
        />
      ))}
    </svg>
  );
}

// ── Gold horizontal line connecting SF to Final ───────────────────────────────
function DHLine({ y, height, delay = 0 }: { y: number; height: number; delay?: number }) {
  return (
    <svg width={D_HLINE_W} height={height} className="shrink-0" style={{ marginTop: D_HDR_H }}>
      <motion.path
        d={`M 0,${y} L ${D_HLINE_W},${y}`}
        fill="none"
        stroke="rgba(245,200,66,0.45)"
        strokeWidth="1.5"
        strokeLinecap="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{
          pathLength: { duration: 0.18, delay, ease: "easeInOut" },
          opacity:    { duration: 0.12, delay },
        }}
      />
    </svg>
  );
}

// ── Column of N stacked, positioned cards ─────────────────────────────────────
function DCol({ matches, centers, label, fromLeft, delay }: {
  matches: BracketMatch[]; centers: number[]; label: React.ReactNode;
  fromLeft: boolean; delay: number;
}) {
  return (
    <div className="shrink-0" style={{ width: D_CARD_W }}>
      <div className="flex items-center justify-center" style={{ height: D_HDR_H }}>{label}</div>
      <div className="relative" style={{ height: D_BRACKET_H }}>
        {matches.map((m, i) => (
          <div key={m.match_id} className="absolute" style={{ top: centers[i] - D_CARD_H / 2 }}>
            <DCard match={m} fromLeft={fromLeft} delay={delay + i * 0.055} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Single card centred at a given y ─────────────────────────────────────────
function DSingleCol({ match, center, label, fromLeft, delay }: {
  match: BracketMatch; center: number; label: React.ReactNode;
  fromLeft: boolean; delay: number;
}) {
  return (
    <div className="shrink-0" style={{ width: D_CARD_W }}>
      <div className="flex items-center justify-center" style={{ height: D_HDR_H }}>{label}</div>
      <div className="relative" style={{ height: D_BRACKET_H }}>
        <div className="absolute" style={{ top: center - D_CARD_H / 2 }}>
          <DCard match={match} fromLeft={fromLeft} delay={delay} />
        </div>
      </div>
    </div>
  );
}

// ── Wider Final card column ───────────────────────────────────────────────────
function DFinalCol({ match, center, label, delay }: {
  match: BracketMatch; center: number; label: React.ReactNode; delay: number;
}) {
  return (
    <div className="shrink-0" style={{ width: D_FINAL_W }}>
      <div className="flex items-center justify-center" style={{ height: D_HDR_H }}>{label}</div>
      <div className="relative" style={{ height: D_BRACKET_H }}>
        <div className="absolute" style={{ top: center - D_CARD_H / 2 }}>
          <DCard match={match} isFinal={true} delay={delay} />
        </div>
      </div>
    </div>
  );
}

// ── Full animated bracket diagram ────────────────────────────────────────────
function BracketDiagram({ rounds }: { rounds: BracketRound[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale]  = useState(1);

  useLayoutEffect(() => {
    const update = () => {
      const w = containerRef.current?.clientWidth ?? D_NATURAL_W;
      setScale(Math.min(1, w / D_NATURAL_W));
    };
    update();
    const ro = new ResizeObserver(update);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const r16 = rounds.find(r => r.round === "Round of 16")?.matches ?? [];
  const qf  = rounds.find(r => r.round === "Quarter-Final")?.matches ?? [];
  const sf  = rounds.find(r => r.round === "Semi-Final")?.matches ?? [];
  const fin = rounds.find(r => r.round === "Final")?.matches ?? [];

  if (r16.length < 8 || qf.length < 4 || sf.length < 2 || !fin[0]) return null;

  const r16L = r16.slice(0, 4);
  const r16R = r16.slice(4);
  const qfL  = qf.slice(0, 2);
  const qfR  = qf.slice(2);

  const r16Label  = <DLabel text="Round of 16"  icon="⚡" />;
  const qfLabel   = <DLabel text="Quarterfinals" icon="⚽" />;
  const sfLabel   = <DLabel text="Semifinals"    icon="🌟" />;
  const finLabel  = <DLabel text="Final"         icon="⭐" />;

  return (
    // Outer: measures available width, collapses to scaled height
    <div ref={containerRef} className="w-full overflow-hidden" style={{ height: D_NATURAL_H * scale }}>
      {/* Inner: scaled to fit, centred via left:50% + negative margin */}
      <div style={{
        transform:       `scale(${scale})`,
        transformOrigin: "top center",
        width:           D_NATURAL_W,
        position:        "relative",
        left:            "50%",
        marginLeft:      -D_NATURAL_W / 2,
      }}>
        <div className="flex items-start px-6 py-2">

          {/* ── Left R16 → QF → SF ─────────────────────────────────────── */}
          <DCol    matches={r16L}  centers={D_R16_Y}      label={r16Label} fromLeft={true}  delay={0} />
          <DConnector from={D_R16_Y} to={D_QF_Y}          height={D_BRACKET_H} delay={0.12} />
          <DCol    matches={qfL}   centers={D_QF_Y}       label={qfLabel}  fromLeft={true}  delay={0.22} />
          <DConnector from={D_QF_Y}  to={[D_SF_Y]}        height={D_BRACKET_H} delay={0.35} />
          <DSingleCol match={sf[0]}  center={D_SF_Y}      label={sfLabel}  fromLeft={true}  delay={0.48} />
          <DHLine y={D_SF_Y} height={D_BRACKET_H} delay={0.60} />

          {/* ── Final (centre) ─────────────────────────────────────────── */}
          <DFinalCol match={fin[0]} center={D_SF_Y} label={finLabel} delay={0.70} />

          {/* ── Right SF → QF → R16 ────────────────────────────────────── */}
          <DHLine y={D_SF_Y} height={D_BRACKET_H} delay={0.60} />
          <DSingleCol match={sf[1]}  center={D_SF_Y}      label={sfLabel}  fromLeft={false} delay={0.48} />
          <DConnector from={[D_SF_Y]} to={D_QF_Y}         height={D_BRACKET_H} delay={0.35} />
          <DCol    matches={qfR}   centers={D_QF_Y}       label={qfLabel}  fromLeft={false} delay={0.22} />
          <DConnector from={D_QF_Y}  to={D_R16_Y}         height={D_BRACKET_H} delay={0.12} />
          <DCol    matches={r16R}  centers={D_R16_Y}      label={r16Label} fromLeft={false} delay={0} />

        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Round-detail match cards (existing tab view)
// ═══════════════════════════════════════════════════════════════════════════════

function TeamRow({ team, prob, isWinner }: { team: string; prob: number; isWinner: boolean }) {
  const pct = (prob * 100).toFixed(1);
  return (
    <div className={`relative flex items-center gap-2.5 px-3 py-[11px] ${isWinner ? "bg-gold-500/[0.06]" : ""}`}>
      {isWinner && <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gold-400 rounded-r-sm" />}
      <FlagIcon team={team} className="w-7 h-[19px] rounded-sm shrink-0 shadow-sm" />
      <span className={`text-[13px] font-medium flex-1 truncate leading-tight ${isWinner ? "text-white" : "text-slate-400"}`}>{team}</span>
      <div className="w-20 bg-navy-700/80 rounded-full h-[5px] shrink-0 overflow-hidden hidden sm:block">
        <div className={`h-[5px] rounded-full transition-all ${isWinner ? "bg-gold-400" : "bg-slate-600"}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`font-bold text-[13px] tabular-nums w-[46px] text-right shrink-0 ${isWinner ? "text-gold-400" : "text-slate-500"}`}>{pct}%</span>
    </div>
  );
}

function MatchCard({ match }: { match: BracketMatch }) {
  return (
    <div className="rounded-xl border border-navy-600/60 bg-navy-800 overflow-hidden hover:border-navy-500/80 transition-colors">
      <TeamRow team={match.team1} prob={match.team1_win_prob} isWinner={match.predicted_winner === match.team1} />
      <div className="h-px bg-navy-600/40 mx-3" />
      <TeamRow team={match.team2} prob={match.team2_win_prob} isWinner={match.predicted_winner === match.team2} />
    </div>
  );
}

function FinalTeamRow({ team, prob, isWinner }: { team: string; prob: number; isWinner: boolean }) {
  const pct = (prob * 100).toFixed(1);
  return (
    <div className={`relative flex items-center gap-3 px-5 py-3 ${isWinner ? "bg-gold-500/[0.05]" : ""}`}>
      {isWinner && <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gold-400" />}
      <FlagIcon team={team} className="w-10 h-[27px] rounded shrink-0 shadow-md" />
      <span className={`text-[15px] font-semibold flex-1 truncate ${isWinner ? "text-white" : "text-slate-400"}`}>{team}</span>
      <span
        className={`font-black text-[20px] tabular-nums ${isWinner ? "text-gold-400" : "text-slate-500"}`}
        style={isWinner ? { textShadow: "0 0 16px rgba(245,200,66,0.3)" } : {}}
      >{pct}%</span>
    </div>
  );
}

function FinalCard({ match }: { match: BracketMatch }) {
  return (
    <div className="rounded-2xl overflow-hidden mx-auto max-w-md" style={{
      background: "linear-gradient(160deg, rgba(197,130,39,0.14) 0%, rgba(14,16,32,1) 70%)",
      border: "1.5px solid rgba(245,200,66,0.3)",
      boxShadow: "0 0 48px rgba(245,200,66,0.06), inset 0 1px 0 rgba(245,200,66,0.1)",
    }}>
      <div className="flex items-center justify-center gap-2 py-3 border-b border-gold-500/10">
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-gold-500/70">World Cup Final</span>
      </div>
      <div className="py-2">
        <FinalTeamRow team={match.team1} prob={match.team1_win_prob} isWinner={match.predicted_winner === match.team1} />
        <div className="flex items-center gap-3 px-5 py-1">
          <div className="flex-1 h-px bg-navy-600/50" />
          <span className="text-[10px] text-slate-600 font-medium uppercase tracking-widest">vs</span>
          <div className="flex-1 h-px bg-navy-600/50" />
        </div>
        <FinalTeamRow team={match.team2} prob={match.team2_win_prob} isWinner={match.predicted_winner === match.team2} />
      </div>
    </div>
  );
}

// ─── Champion banner ──────────────────────────────────────────────────────────
function ChampionBanner({ champion }: { champion: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative flex items-center gap-4 rounded-2xl px-6 py-4 overflow-hidden"
      style={{
        background: "linear-gradient(135deg, rgba(197,130,39,0.18) 0%, rgba(14,16,32,1) 60%)",
        border:     "1.5px solid rgba(245,200,66,0.28)",
        boxShadow:  "0 0 40px rgba(245,200,66,0.05)",
      }}
    >
      <div className="pointer-events-none absolute left-0 top-0 w-40 h-full">
        <div className="absolute inset-0 bg-gold-500/[0.07] blur-2xl rounded-2xl" />
      </div>
      <span className="text-3xl shrink-0 relative">🏆</span>
      <div className="relative">
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gold-500/60 mb-0.5">Predicted Champion</div>
        <div className="flex items-center gap-2.5">
          <FlagIcon team={champion} className="w-8 h-[21px] rounded-sm shadow" />
          <span className="text-xl font-bold text-white">{champion}</span>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Group standings ──────────────────────────────────────────────────────────
const PLACE_LABEL = ["1st", "2nd", "3rd", "4th"];
const PLACE_COLOR = ["text-gold-400", "text-slate-300", "text-amber-700/90", "text-slate-600"];

function GroupStandings({ standings }: { standings: Record<string, string[]> }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-navy-600/60 bg-navy-800/50 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-slate-300 hover:text-white transition-colors"
      >
        <span className="uppercase tracking-wider text-xs">Expected Group Standings</span>
        <span className="text-slate-500 text-xs">{open ? "▲ Hide" : "▼ Show"}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="standings"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-px bg-navy-600/30 border-t border-navy-600/30">
              {Object.entries(standings).map(([groupId, teams]) => (
                <div key={groupId} className="bg-navy-900 px-3 py-2.5">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">Group {groupId}</div>
                  {teams.map((team, i) => (
                    <div key={team} className="flex items-center gap-1.5 py-[3px]">
                      <span className={`text-[10px] font-bold w-6 shrink-0 ${PLACE_COLOR[i]}`}>{PLACE_LABEL[i]}</span>
                      <FlagIcon team={team} className="w-5 h-[13px] rounded-sm shrink-0" />
                      <span className={`text-[11px] truncate ${i === 3 ? "text-slate-600 line-through" : "text-slate-300"}`}>{team}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Round detail tabs ────────────────────────────────────────────────────────
function BracketRounds({ rounds }: { rounds: BracketRound[] }) {
  const roundNames = rounds.map(r => r.round);
  const [activeRound, setActiveRound] = useState(roundNames[0] ?? "Round of 32");
  const active = rounds.find(r => r.round === activeRound);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-1 overflow-x-auto pb-1 scrollbar-none">
        {roundNames.map(name => {
          const isActive = name === activeRound;
          return (
            <button
              key={name}
              onClick={() => setActiveRound(name)}
              className={`shrink-0 px-3.5 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
                isActive ? "bg-fifa-blue text-white" : "text-slate-500 hover:text-slate-300 hover:bg-navy-700"
              }`}
            >
              {ROUND_LABELS[name] ?? name}
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {active && (
          <motion.div
            key={activeRound}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
          >
            {activeRound === "Final" ? (
              <div className="py-2"><FinalCard match={active.matches[0]} /></div>
            ) : (
              <div className={`grid gap-3 ${
                active.matches.length >= 8
                  ? "grid-cols-1 sm:grid-cols-2 xl:grid-cols-4"
                  : active.matches.length >= 4
                  ? "grid-cols-1 sm:grid-cols-2"
                  : "grid-cols-1 sm:grid-cols-2 max-w-xl"
              }`}>
                {active.matches.map(m => <MatchCard key={m.match_id} match={m} />)}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Champion Odds (from Monte Carlo simulation) ──────────────────────────────
const MEDALS    = ["🥇", "🥈", "🥉"];
const BAR_COLORS = ["bg-gold-400", "bg-slate-400", "bg-amber-700", "bg-pitch-400"];

function ChampionOdds({ teams }: { teams: TeamSimResult[] }) {
  const top10 = [...teams].sort((a, b) => b.champion - a.champion).slice(0, 10);
  const maxPct = top10[0].champion;
  return (
    <div className="space-y-2">
      {top10.map((t, i) => (
        <motion.div
          key={t.team}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.04 }}
          className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border transition-colors ${
            i === 0 ? "bg-gold-500/[0.06] border-gold-500/20" : "bg-navy-800 border-navy-700/60"
          }`}
        >
          <div className="w-6 text-center shrink-0">
            {i < 3 ? <span className="text-sm">{MEDALS[i]}</span> : <span className="text-slate-600 text-xs">{i + 1}</span>}
          </div>
          <FlagIcon team={t.team} className="w-8 h-6 rounded shrink-0" />
          <span className={`text-sm font-medium flex-1 truncate ${i === 0 ? "text-gold-300" : "text-white"}`}>{t.team}</span>
          <span className="text-slate-500 text-xs shrink-0 hidden sm:block">{t.group}</span>
          <div className="w-28 bg-navy-700 rounded-full h-1.5 shrink-0 hidden sm:block overflow-hidden">
            <div className={`h-1.5 rounded-full transition-all ${BAR_COLORS[Math.min(i, 3)]}`} style={{ width: `${(t.champion / maxPct) * 100}%` }} />
          </div>
          <span className={`font-bold text-sm tabular-nums w-14 text-right shrink-0 ${
            i === 0 ? "text-gold-400" : i === 1 ? "text-slate-300" : i === 2 ? "text-amber-600" : "text-pitch-400"
          }`}>{(t.champion * 100).toFixed(1)}%</span>
        </motion.div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Page
// ═══════════════════════════════════════════════════════════════════════════════

export default function SimulatePage() {
  const bracket    = useBracket();
  const simulation = useSimulation();

  return (
    <main className="min-h-screen bg-navy-900">

      {/* ── Hero ── */}
      <section className="relative overflow-hidden border-b border-navy-700 py-14 px-6 md:px-14">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 -translate-x-1/2 top-0 w-[700px] h-[320px] rounded-full bg-fifa-blue/[0.04] blur-3xl" />
          <div className="absolute left-1/2 -translate-x-1/2 top-4 w-[220px] h-[180px] rounded-full bg-gold-500/[0.05] blur-2xl" />
        </div>
        <div className="relative max-w-3xl mx-auto text-center">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-pitch-400 mb-3">
              Model Prediction · Head-to-Head Win Probabilities
            </p>
            <h1 className="font-anton text-4xl md:text-5xl text-white tracking-wide mb-3">BRACKET PREDICTOR</h1>
            <p className="text-slate-400 text-sm max-w-xl mx-auto leading-relaxed">
              The model&apos;s most likely path through the tournament.
              Each matchup shows the head-to-head win probability for that specific game.
            </p>
          </motion.div>
        </div>
      </section>

      {/* ── Content ── */}
      <div className="max-w-screen-xl mx-auto px-4 md:px-6 py-10 space-y-10">

        {bracket.loading && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-10 h-10 border-2 border-fifa-blue border-t-transparent rounded-full animate-spin" />
            <p className="text-slate-400 text-sm">Computing bracket predictions…</p>
          </div>
        )}

        {bracket.error && (
          <div className="max-w-lg mx-auto bg-red-950/40 border border-red-800 rounded-xl px-5 py-4 text-red-300 text-sm text-center">
            Prediction failed: {bracket.error}.{" "}
            <span className="text-red-400">Make sure the backend is running on port 8000.</span>
          </div>
        )}

        {bracket.data && (
          <>
            {/* ── Champion banner ── */}
            <ChampionBanner champion={bracket.data.champion} />

            {/* ── Visual bracket diagram (desktop only) ── */}
            <section className="hidden md:block">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Predicted Bracket
                </h2>
                <span className="text-xs text-slate-600 hidden lg:block">
                  R16 → QF → SF → Final
                </span>
              </div>
              <div
                className="relative rounded-2xl border border-navy-600/80 overflow-hidden"
                style={{
                  background: "linear-gradient(180deg, rgba(21,24,41,1) 0%, rgba(14,16,32,1) 100%)",
                  boxShadow:  "inset 0 1px 0 rgba(255,255,255,0.03)",
                }}
              >
                {/* centre glow */}
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <div className="w-72 h-72 rounded-full bg-gold-500/[0.03] blur-3xl" />
                </div>
                {/* top accent */}
                <div className="absolute top-0 left-[25%] right-[25%] h-px bg-gradient-to-r from-transparent via-gold-500/15 to-transparent" />
                <div className="relative py-6">
                  <BracketDiagram rounds={bracket.data.rounds} />
                </div>
              </div>
            </section>

            {/* ── Group standings ── */}
            <GroupStandings standings={bracket.data.group_standings} />

            {/* ── Round detail tabs ── */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Knockout Bracket</h2>
                <span className="text-xs text-slate-600 hidden sm:block">
                  {new Date(bracket.data.generated_at).toLocaleString()}
                </span>
              </div>
              <div
                className="relative rounded-2xl border border-navy-600/80 overflow-hidden p-5"
                style={{
                  background: "linear-gradient(180deg, rgba(21,24,41,1) 0%, rgba(14,16,32,1) 100%)",
                  boxShadow:  "inset 0 1px 0 rgba(255,255,255,0.04)",
                }}
              >
                <BracketRounds rounds={bracket.data.rounds} />
              </div>
            </section>

            {/* ── Champion Odds (Monte Carlo) ── */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Top 10 Champion Odds</h2>
                {simulation.data && (
                  <span className="text-xs text-slate-600 hidden sm:block">
                    {simulation.data.n_simulations.toLocaleString()} Monte Carlo simulations
                  </span>
                )}
              </div>
              {simulation.loading && (
                <div className="flex items-center gap-2 text-slate-500 text-sm py-4">
                  <div className="w-4 h-4 border-2 border-slate-600 border-t-transparent rounded-full animate-spin" />
                  Loading simulation odds…
                </div>
              )}
              {simulation.data && <ChampionOdds teams={simulation.data.teams} />}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
