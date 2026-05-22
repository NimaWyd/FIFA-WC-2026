"use client";

import { useState, useRef, useLayoutEffect, useEffect } from "react";
import { motion, AnimatePresence, useMotionValue, useTransform, animate } from "framer-motion";
import dynamic from "next/dynamic";
import FlagIcon from "@/components/FlagIcon";
import { useBracket } from "@/hooks/useBracket";
import { useSimulation } from "@/hooks/useSimulation";
import type { BracketMatch, BracketRound, TeamSimResult } from "@/lib/types";

const TrophyEmbed = dynamic(() => import("@/components/TrophyEmbed"), { ssr: false });

// ─── Bracket layout constants (linear: R32 → R16 → QF → SF → Final → Champion) ─
const D_ROW_H    = 26
const D_CARD_H   = D_ROW_H * 2 + 2         // 54
const D_CARD_W   = 152
const D_FINAL_W  = 172
const D_CHAMP_W  = 210
const D_GAP      = 8
const D_SVG_W    = 26
const D_HDR_H    = 28

// R32 compact card dimensions
const D_R32_ROW_H  = 18
const D_R32_CARD_H = D_R32_ROW_H * 2 + 2   // 38
const D_R32_CARD_W = 136
const D_R32_GAP    = 4

// Column height is now driven by 16 R32 matches
const D_COL_H = 16 * D_R32_CARD_H + 15 * D_R32_GAP  // 608 + 60 = 668

// Vertical centres per round — everything derived from R32 spacing
const D_R32_Y = Array.from({ length: 16 }, (_, i) => i * (D_R32_CARD_H + D_R32_GAP) + D_R32_CARD_H / 2)
const D_R16_Y = Array.from({ length: 8 },  (_, i) => (D_R32_Y[i * 2] + D_R32_Y[i * 2 + 1]) / 2)
const D_QF_Y  = [0, 1, 2, 3].map(i => (D_R16_Y[i * 2] + D_R16_Y[i * 2 + 1]) / 2)
const D_SF_Y  = [0, 1].map(i => (D_QF_Y[i * 2] + D_QF_Y[i * 2 + 1]) / 2)
const D_FIN_Y = (D_SF_Y[0] + D_SF_Y[1]) / 2

// 3rd-place playoff x-offset: centered under the Final column
// Final left edge = 696; Final width = 172; 3rd-place card width = 172 → same width, same x
const D_3P_X = D_R32_CARD_W + D_SVG_W + D_CARD_W + D_SVG_W + D_CARD_W + D_SVG_W + D_CARD_W + D_SVG_W  // 696

const D_3P_H  = 96
const D_NAT_H = D_HDR_H + D_COL_H + 16 + D_3P_H   // 28+668+16+96 = 808
const D_NAT_W =
  D_R32_CARD_W + D_SVG_W + D_CARD_W + D_SVG_W + D_CARD_W + D_SVG_W + D_CARD_W + D_SVG_W + D_FINAL_W + D_SVG_W + D_CHAMP_W + 40
// 136+26+152+26+152+26+152+26+172+26+210+40 = 1144

// ─── Round tab labels (mobile) ────────────────────────────────────────────────
const ROUND_LABELS: Record<string, string> = {
  "Round of 32":       "R32",
  "Round of 16":       "R16",
  "Quarter-Final":     "QF",
  "Semi-Final":        "SF",
  "3rd Place Playoff": "3rd",
  "Final":             "Final",
};

// ─── Column header label ──────────────────────────────────────────────────────
function DLabel({ text }: { text: string }) {
  return (
    <span className="font-jb text-[9px] uppercase tracking-[0.18em]" style={{ color: "rgba(245,239,225,0.38)" }}>
      {text}
    </span>
  );
}

// ─── Team row inside a card ───────────────────────────────────────────────────
function DRow({ team, prob, isWinner, large = false, compact = false }: {
  team: string; prob: number; isWinner: boolean; large?: boolean; compact?: boolean;
}) {
  const rowH = compact ? D_R32_ROW_H : D_ROW_H;
  return (
    <div
      className={`relative flex items-center gap-1 ${compact ? "px-1.5" : "px-2 gap-1.5"}`}
      style={{ height: rowH }}
    >
      {isWinner && (
        <div
          className="absolute left-0 top-0 bottom-0 rounded-r"
          style={{ width: 2.5, background: "#f5c842" }}
        />
      )}
      <FlagIcon
        team={team}
        className={`rounded-sm shrink-0 ${
          large   ? "w-6 h-[16px]"    :
          compact ? "w-[12px] h-[8px]" :
                    "w-[15px] h-[10px]"
        }`}
      />
      <span
        className={`flex-1 truncate font-anton leading-none ${
          large ? "text-[13px]" : compact ? "text-[10px]" : "text-[11.5px]"
        }`}
        style={{ color: isWinner ? "#f5efe1" : "rgba(245,239,225,0.3)" }}
      >
        {team}
      </span>
      <span
        className={`font-jb tabular-nums shrink-0 ${compact ? "text-[8px]" : "text-[9px]"}`}
        style={{ color: isWinner ? "#f5c842" : "rgba(245,239,225,0.22)" }}
      >
        {(prob * 100).toFixed(0)}%
      </span>
    </div>
  );
}

// ─── Match card ───────────────────────────────────────────────────────────────
function DCard({ match, variant = "default", delay = 0 }: {
  match: BracketMatch;
  variant?: "default" | "sf" | "final" | "compact";
  delay?: number;
}) {
  const w = variant === "final" ? D_FINAL_W : variant === "compact" ? D_R32_CARD_W : D_CARD_W;
  const h = variant === "compact" ? D_R32_CARD_H : D_CARD_H;
  const cardStyle: React.CSSProperties =
    variant === "final" ? {
      width: w, height: h, borderRadius: 4,
      background: "rgba(245,200,66,0.07)",
      border: "1px solid rgba(245,200,66,0.5)",
      boxShadow: "0 0 14px rgba(245,200,66,0.07)",
    } : variant === "sf" ? {
      width: w, height: h, borderRadius: 4,
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(245,200,66,0.2)",
    } : variant === "compact" ? {
      width: w, height: h, borderRadius: 3,
      background: "rgba(255,255,255,0.025)",
      border: "1px solid rgba(255,255,255,0.06)",
    } : {
      width: w, height: h, borderRadius: 4,
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.07)",
    };

  const isCompact = variant === "compact";
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.26, delay, ease: "easeOut" }}
      className="overflow-hidden shrink-0"
      style={cardStyle}
    >
      <DRow team={match.team1} prob={match.team1_win_prob} isWinner={match.predicted_winner === match.team1} large={variant === "final"} compact={isCompact} />
      <div style={{ height: 1, margin: `0 ${isCompact ? 5 : 8}px`, background: "rgba(255,255,255,0.05)" }} />
      <DRow team={match.team2} prob={match.team2_win_prob} isWinner={match.predicted_winner === match.team2} large={variant === "final"} compact={isCompact} />
    </motion.div>
  );
}

// ─── SVG connector between rounds ────────────────────────────────────────────
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
          stroke="rgba(255,255,255,0.10)"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{
            pathLength: { duration: 0.32, delay: delay + i * 0.015, ease: "easeInOut" },
            opacity: { duration: 0.1, delay },
          }}
        />
      ))}
    </svg>
  );
}

// ─── Column of cards at specified vertical centres ────────────────────────────
function DCol({ matches, centers, label, variant = "default", delay, cardH = D_CARD_H }: {
  matches: BracketMatch[];
  centers: number[];
  label: React.ReactNode;
  variant?: "default" | "sf" | "final" | "compact";
  delay: number;
  cardH?: number;
}) {
  const w = variant === "final" ? D_FINAL_W : variant === "compact" ? D_R32_CARD_W : D_CARD_W;
  return (
    <div className="shrink-0" style={{ width: w }}>
      <div className="flex items-center justify-center" style={{ height: D_HDR_H }}>{label}</div>
      <div className="relative" style={{ height: D_COL_H }}>
        {matches.map((m, i) => (
          <div key={m.match_id} className="absolute" style={{ top: centers[i] - cardH / 2 }}>
            <DCard match={m} variant={variant} delay={delay + i * 0.04} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Champion column ──────────────────────────────────────────────────────────
const CHAMP_PARTICLES = [
  { x: 18,  y: 22, size: 2, delay: 0.0, dur: 3.2 },
  { x: 82,  y: 18, size: 2, delay: 1.1, dur: 2.9 },
  { x: 12,  y: 74, size: 1.5, delay: 0.6, dur: 3.5 },
  { x: 88,  y: 70, size: 2, delay: 1.7, dur: 2.8 },
  { x: 50,  y: 8,  size: 1.5, delay: 2.0, dur: 3.0 },
];

function DChampionCol({ champion, championOdds, delay }: {
  champion: string; championOdds?: number; delay: number;
}) {
  return (
    <div className="shrink-0" style={{ width: D_CHAMP_W }}>
      <div className="flex items-center justify-center" style={{ height: D_HDR_H }}>
        <DLabel text="Champion" />
      </div>
      <div className="relative flex flex-col items-center justify-center" style={{ height: D_COL_H }}>
        {/* Trophy frame */}
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.92 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay, duration: 0.5, ease: [0.21, 1, 0.73, 1] }}
          className="relative"
          style={{ width: 152, height: 220 }}
        >
          {/* Glow behind trophy */}
          <div
            className="pointer-events-none absolute inset-0 blur-2xl"
            style={{ background: "radial-gradient(circle, rgba(245,200,66,0.22) 0%, transparent 70%)", transform: "scale(1.6)" }}
          />
          {/* Pulsing border */}
          <motion.div
            className="pointer-events-none absolute inset-0 rounded-md"
            animate={{ opacity: [0.3, 0.8, 0.3] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            style={{ boxShadow: "0 0 0 1px rgba(245,200,66,0.3), 0 12px 40px rgba(245,200,66,0.12)" }}
          />
          {/* Floating particles */}
          {CHAMP_PARTICLES.map((p, k) => (
            <motion.div
              key={k}
              className="pointer-events-none absolute rounded-full"
              style={{ left: `${p.x}%`, top: `${p.y}%`, width: p.size, height: p.size, background: "#f5c842" }}
              animate={{ y: [0, -14, 0], opacity: [0, 0.5, 0] }}
              transition={{ duration: p.dur, delay: p.delay, repeat: Infinity, ease: "easeInOut" }}
            />
          ))}
          <div className="relative w-full h-full rounded-md overflow-hidden">
            <TrophyEmbed className="w-full h-full" />
          </div>
        </motion.div>

        {/* Team name */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: delay + 0.18, duration: 0.32 }}
          className="font-anton text-[42px] leading-none mt-3 text-center"
          style={{ color: "#f5c842", textShadow: "0 0 28px rgba(245,200,66,0.3)" }}
        >
          {champion}
        </motion.div>

        {/* Odds caption */}
        {championOdds !== undefined && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: delay + 0.32 }}
            className="font-jb text-[9px] tracking-[0.18em] mt-1.5 text-center"
            style={{ color: "rgba(245,239,225,0.4)" }}
          >
            {(championOdds * 100).toFixed(1)}% TO WIN
          </motion.div>
        )}
      </div>
    </div>
  );
}

// ─── Full linear bracket diagram ─────────────────────────────────────────────
function BracketDiagram({ rounds, champion, championOdds }: {
  rounds: BracketRound[];
  champion: string;
  championOdds?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useLayoutEffect(() => {
    const update = () => {
      const w = containerRef.current?.clientWidth ?? D_NAT_W;
      setScale(Math.min(1, w / D_NAT_W));
    };
    update();
    const ro = new ResizeObserver(update);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const r32 = rounds.find(r => r.round === "Round of 32")?.matches ?? [];
  const r16 = rounds.find(r => r.round === "Round of 16")?.matches ?? [];
  const qf  = rounds.find(r => r.round === "Quarter-Final")?.matches ?? [];
  const sf  = rounds.find(r => r.round === "Semi-Final")?.matches ?? [];
  const fin = rounds.find(r => r.round === "Final")?.matches ?? [];
  const tp  = rounds.find(r => r.round === "3rd Place Playoff")?.matches?.[0];

  const hasR32 = r32.length >= 16;
  if (r16.length < 8 || qf.length < 4 || sf.length < 2 || !fin[0]) return null;

  return (
    <div ref={containerRef} className="w-full" style={{ height: D_NAT_H * scale }}>
      <div
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "top left",
          width: D_NAT_W,
          height: D_NAT_H,
        }}
      >
        {/* Main bracket row */}
        <div className="flex items-start" style={{ paddingLeft: 20, paddingTop: 0 }}>
          {hasR32 && (
            <>
              <DCol matches={r32} centers={D_R32_Y} label={<DLabel text="Round of 32" />} variant="compact" cardH={D_R32_CARD_H} delay={0} />
              <DConnector from={D_R32_Y} to={D_R16_Y} height={D_COL_H} delay={0.06} />
            </>
          )}
          <DCol matches={r16} centers={D_R16_Y} label={<DLabel text="Round of 16" />} delay={hasR32 ? 0.12 : 0} />
          <DConnector from={D_R16_Y} to={D_QF_Y} height={D_COL_H} delay={hasR32 ? 0.20 : 0.10} />
          <DCol matches={qf}  centers={D_QF_Y}  label={<DLabel text="Quarter-Finals" />} delay={hasR32 ? 0.28 : 0.20} />
          <DConnector from={D_QF_Y}  to={D_SF_Y}  height={D_COL_H} delay={hasR32 ? 0.36 : 0.30} />
          <DCol matches={sf}  centers={D_SF_Y}  label={<DLabel text="Semi-Finals" />} variant="sf" delay={hasR32 ? 0.44 : 0.40} />
          <DConnector from={D_SF_Y}  to={[D_FIN_Y]} height={D_COL_H} delay={hasR32 ? 0.52 : 0.50} />
          <DCol matches={fin} centers={[D_FIN_Y]} label={<DLabel text="Final" />} variant="final" delay={hasR32 ? 0.58 : 0.58} />
          <DConnector from={[D_FIN_Y]} to={[D_FIN_Y]} height={D_COL_H} delay={hasR32 ? 0.66 : 0.66} />
          <DChampionCol champion={champion} championOdds={championOdds} delay={hasR32 ? 0.74 : 0.74} />
        </div>

        {/* 3rd Place Playoff — aligned with Final column (same x, same width) */}
        {tp && (
          <div
            className="flex flex-col items-start gap-1.5"
            style={{ paddingLeft: 20 + (hasR32 ? D_3P_X : D_3P_X - D_R32_CARD_W - D_SVG_W), paddingTop: 14 }}
          >
            <div className="flex items-center justify-center" style={{ width: D_FINAL_W, height: D_HDR_H }}>
              <DLabel text="3rd Place Playoff" />
            </div>
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.26, delay: 0.9 }}
              className="overflow-hidden shrink-0"
              style={{
                width: D_FINAL_W, height: D_CARD_H, borderRadius: 4,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(160,100,40,0.3)",
              }}
            >
              <DRow team={tp.team1} prob={tp.team1_win_prob} isWinner={tp.predicted_winner === tp.team1} large />
              <div style={{ height: 1, margin: "0 8px", background: "rgba(255,255,255,0.05)" }} />
              <DRow team={tp.team2} prob={tp.team2_win_prob} isWinner={tp.predicted_winner === tp.team2} large />
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Mobile tab view (round by round) ────────────────────────────────────────
function TeamRow({ team, prob, isWinner }: { team: string; prob: number; isWinner: boolean }) {
  const pct = (prob * 100).toFixed(1);
  return (
    <div className={`relative flex items-center gap-1.5 sm:gap-2.5 px-2 py-[7px] sm:px-3 sm:py-[11px] ${isWinner ? "bg-gold-500/[0.06]" : ""}`}>
      {isWinner && <div className="absolute left-0 top-0 bottom-0 w-[2.5px] bg-gold-400 rounded-r-sm" />}
      <FlagIcon team={team} className="w-5 h-[14px] sm:w-7 sm:h-[19px] rounded-sm shrink-0 shadow-sm" />
      <span className={`text-[11px] sm:text-[13px] font-medium flex-1 truncate leading-tight ${isWinner ? "text-white" : "text-slate-400"}`}>{team}</span>
      <div className="w-20 bg-navy-700/80 rounded-full h-[5px] shrink-0 overflow-hidden hidden sm:block">
        <div className={`h-[5px] rounded-full transition-all ${isWinner ? "bg-gold-400" : "bg-slate-600"}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`font-bold tabular-nums text-right shrink-0 w-[32px] text-[10px] sm:w-[46px] sm:text-[13px] ${isWinner ? "text-gold-400" : "text-slate-500"}`}>{pct}%</span>
    </div>
  );
}

function MatchCard({ match }: { match: BracketMatch }) {
  return (
    <div className="rounded-lg sm:rounded-xl border border-navy-600/60 bg-navy-800 overflow-hidden hover:border-navy-500/80 transition-colors">
      <TeamRow team={match.team1} prob={match.team1_win_prob} isWinner={match.predicted_winner === match.team1} />
      <div className="h-px bg-navy-600/40 mx-2 sm:mx-3" />
      <TeamRow team={match.team2} prob={match.team2_win_prob} isWinner={match.predicted_winner === match.team2} />
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
        {[match.team1, match.team2].map((team, i) => {
          const prob = i === 0 ? match.team1_win_prob : match.team2_win_prob;
          const isWinner = match.predicted_winner === team;
          return (
            <div key={team} className={`relative flex items-center gap-3 px-5 ${i === 0 ? "py-3" : "py-3"} ${isWinner ? "bg-gold-500/[0.05]" : ""}`}>
              {isWinner && <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gold-400" />}
              <FlagIcon team={team} className="w-10 h-[27px] rounded shrink-0 shadow-md" />
              <span className={`text-[15px] font-semibold flex-1 truncate ${isWinner ? "text-white" : "text-slate-400"}`}>{team}</span>
              <span className={`font-black text-[20px] tabular-nums ${isWinner ? "text-gold-400" : "text-slate-500"}`} style={isWinner ? { textShadow: "0 0 16px rgba(245,200,66,0.3)" } : {}}>
                {(prob * 100).toFixed(1)}%
              </span>
              {i === 0 && (
                <div className="absolute bottom-0 left-5 right-5 flex items-center gap-3">
                  <div className="flex-1 h-px bg-navy-600/50" />
                  <span className="text-[10px] text-slate-600 font-medium uppercase tracking-widest">vs</span>
                  <div className="flex-1 h-px bg-navy-600/50" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BracketRounds({ rounds }: { rounds: BracketRound[] }) {
  const roundNames = rounds.map(r => r.round);
  const [active, setActive] = useState(roundNames[0] ?? "Round of 32");
  const activeRound = rounds.find(r => r.round === active);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-1 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none]">
        {roundNames.map(name => {
          const isActive = name === active;
          return (
            <button
              key={name}
              onClick={() => setActive(name)}
              className={`shrink-0 px-3.5 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
                isActive
                  ? "bg-navy-600 text-white border border-white/10"
                  : "text-slate-500 hover:text-slate-300 hover:bg-navy-700"
              }`}
            >
              {ROUND_LABELS[name] ?? name}
            </button>
          );
        })}
      </div>
      <AnimatePresence mode="wait">
        {activeRound && (
          <motion.div
            key={active}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
          >
            {active === "Final" ? (
              <div className="py-2"><FinalCard match={activeRound.matches[0]} /></div>
            ) : (
              <div className={`grid gap-2 sm:gap-3 ${
                activeRound.matches.length >= 8
                  ? "grid-cols-2 sm:grid-cols-2 xl:grid-cols-4"
                  : activeRound.matches.length >= 4
                  ? "grid-cols-2 sm:grid-cols-2"
                  : "grid-cols-1 sm:grid-cols-2 max-w-sm mx-auto sm:max-w-xl"
              }`}>
                {activeRound.matches.map(m => <MatchCard key={m.match_id} match={m} />)}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Group standings ──────────────────────────────────────────────────────────
const PLACE_LABEL = ["1st", "2nd", "3rd", "4th"];
const PLACE_COLOR = ["text-gold-400", "text-slate-300", "text-amber-700/90", "text-slate-600"];

function GroupStandings({ standings }: { standings: Record<string, string[]> }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.07)", background: "rgba(255,255,255,0.02)" }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
      >
        <span className="font-jb text-[10px] uppercase tracking-[0.18em]" style={{ color: "rgba(245,239,225,0.45)" }}>
          Expected Group Standings
        </span>
        <span className="font-jb text-[9px]" style={{ color: "rgba(245,239,225,0.3)" }}>{open ? "▲ HIDE" : "▼ SHOW"}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="standings"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div
              className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-px"
              style={{ background: "rgba(255,255,255,0.05)", borderTop: "1px solid rgba(255,255,255,0.06)" }}
            >
              {Object.entries(standings).map(([groupId, teams]) => (
                <div key={groupId} className="px-3 py-2.5" style={{ background: "#090b14" }}>
                  <div className="font-jb text-[9px] uppercase tracking-widest mb-1.5" style={{ color: "rgba(245,239,225,0.35)" }}>
                    Group {groupId}
                  </div>
                  {teams.map((team, i) => (
                    <div key={team} className="flex items-center gap-1.5 py-[3px]">
                      <span className={`font-jb text-[9px] w-6 shrink-0 ${PLACE_COLOR[i]}`}>{PLACE_LABEL[i]}</span>
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

// ─── Animated number for champion odds ───────────────────────────────────────
function AnimatedOdds({ value }: { value: number }) {
  const count = useMotionValue(0);
  const display = useTransform(count, v => (v * 100).toFixed(1) + "%");
  useEffect(() => {
    const ctrl = animate(count, value, { duration: 1.4, delay: 0.5, ease: [0.16, 1, 0.3, 1] });
    return ctrl.stop;
  }, [count, value]);
  return <motion.span className="font-jb font-bold tabular-nums text-gold-400">{display}</motion.span>;
}

// ─── Top 10 champion odds ─────────────────────────────────────────────────────
const MEDALS = ["🥇", "🥈", "🥉"];

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
          className="flex items-center gap-3 px-4 py-2.5 rounded-xl transition-colors"
          style={{
            background: i === 0 ? "rgba(245,200,66,0.06)" : "rgba(255,255,255,0.02)",
            border: `1px solid ${i === 0 ? "rgba(245,200,66,0.2)" : "rgba(255,255,255,0.06)"}`,
          }}
        >
          <div className="w-6 text-center shrink-0">
            {i < 3
              ? <span className="text-sm">{MEDALS[i]}</span>
              : <span className="font-jb text-[10px]" style={{ color: "rgba(245,239,225,0.3)" }}>{i + 1}</span>
            }
          </div>
          <FlagIcon team={t.team} className="w-8 h-6 rounded shrink-0" />
          <span className={`text-sm font-medium flex-1 truncate ${i === 0 ? "text-gold-300" : "text-white"}`}>{t.team}</span>
          <span className="font-jb text-[10px] shrink-0 hidden sm:block" style={{ color: "rgba(245,239,225,0.3)" }}>{t.group}</span>
          <div className="w-28 rounded-full h-1.5 shrink-0 hidden sm:block overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
            <div
              className={`h-1.5 rounded-full transition-all ${i === 0 ? "bg-gold-400" : i === 1 ? "bg-slate-400" : i === 2 ? "bg-amber-700" : "bg-pitch-400"}`}
              style={{ width: `${(t.champion / maxPct) * 100}%` }}
            />
          </div>
          <span
            className={`font-jb font-bold text-sm tabular-nums w-14 text-right shrink-0 ${
              i === 0 ? "text-gold-400" : i === 1 ? "text-slate-300" : i === 2 ? "text-amber-600" : "text-pitch-400"
            }`}
          >
            {(t.champion * 100).toFixed(1)}%
          </span>
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

  const simChampion = simulation.data
    ? [...simulation.data.teams].sort((a, b) => b.champion - a.champion)[0]
    : null;

  const champion     = simChampion?.team ?? bracket.data?.champion ?? "";
  const championOdds = simChampion?.champion;

  return (
    <main className="min-h-screen" style={{ background: "#090b14" }}>
      {/* Radial green glow at bottom */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0"
        style={{ background: "radial-gradient(ellipse at 50% 100%, rgba(34,160,82,0.10) 0%, transparent 55%)", zIndex: 0 }}
      />

      {/* ── Header bar ── */}
      <header
        className="relative z-10 flex items-center justify-between px-8 md:px-14 py-[18px]"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <div className="font-anton text-[18px] tracking-[0.08em] text-white">
          BRACKET PREDICTOR
        </div>
        <div className="hidden md:flex items-center gap-6 font-jb text-[10px] tracking-[0.14em]" style={{ color: "rgba(245,239,225,0.5)" }}>
          {simulation.data && (
            <span>{simulation.data.n_simulations.toLocaleString()} SIMULATIONS</span>
          )}
          {bracket.data && (
            <span style={{ color: "rgba(245,239,225,0.35)" }}>
              {new Date(bracket.data.generated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
          {champion && championOdds !== undefined && (
            <span style={{ color: "#f5c842" }}>
              {champion} · <AnimatedOdds value={championOdds} />
            </span>
          )}
        </div>
        <div className="font-jb text-[10px] tracking-[0.14em]" style={{ color: "rgba(245,239,225,0.3)" }}>
          {bracket.loading ? "COMPUTING…" : bracket.data ? "READY" : ""}
        </div>
      </header>

      {/* ── Main content ── */}
      <div className="relative z-10 px-4 md:px-8 lg:px-14 pt-8 pb-24 space-y-10">

        {/* Loading */}
        {bracket.loading && (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "rgba(255,255,255,0.15)", borderTopColor: "#22a052" }} />
            <p className="font-jb text-[11px] tracking-[0.14em] uppercase" style={{ color: "rgba(245,239,225,0.4)" }}>
              Computing bracket…
            </p>
          </div>
        )}

        {/* Error */}
        {bracket.error && (
          <div className="max-w-lg mx-auto rounded-lg px-5 py-4 text-sm text-center" style={{ background: "rgba(220,50,50,0.08)", border: "1px solid rgba(220,50,50,0.25)", color: "rgba(255,160,160,0.9)" }}>
            Prediction failed: {bracket.error}. Make sure the backend is running on port 8000.
          </div>
        )}

        {bracket.data && (
          <>
            {/* ── Desktop bracket ── */}
            <section className="hidden md:block">
              <div
                className="rounded-xl overflow-hidden"
                style={{
                  background: "rgba(255,255,255,0.015)",
                  border: "1px solid rgba(255,255,255,0.07)",
                  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)",
                }}
              >
                {/* top accent */}
                <div
                  className="pointer-events-none"
                  style={{ height: 1, background: "linear-gradient(90deg, transparent 0%, rgba(245,200,66,0.15) 40%, rgba(245,200,66,0.25) 50%, rgba(245,200,66,0.15) 60%, transparent 100%)" }}
                />
                <div className="py-6 px-2">
                  <BracketDiagram
                    rounds={bracket.data.rounds}
                    champion={champion}
                    championOdds={championOdds}
                  />
                </div>
              </div>
            </section>

            {/* ── Mobile bracket tabs ── */}
            <section className="md:hidden">
              <div
                className="rounded-xl p-4"
                style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}
              >
                <BracketRounds rounds={bracket.data.rounds} />
              </div>
            </section>

            {/* ── Group standings ── */}
            <GroupStandings standings={bracket.data.group_standings} />

            {/* ── Champion odds ── */}
            {(simulation.loading || simulation.data) && (
              <section>
                <div className="flex items-center justify-between mb-4">
                  <span className="font-jb text-[10px] uppercase tracking-[0.18em]" style={{ color: "rgba(245,239,225,0.4)" }}>
                    Champion Odds · Top 10
                  </span>
                  {simulation.loading && (
                    <div className="flex items-center gap-2" style={{ color: "rgba(245,239,225,0.35)" }}>
                      <div className="w-3.5 h-3.5 rounded-full border border-t-transparent animate-spin" style={{ borderColor: "rgba(255,255,255,0.15)", borderTopColor: "#22a052" }} />
                      <span className="font-jb text-[10px] tracking-[0.14em]">Simulating…</span>
                    </div>
                  )}
                  {simulation.data && (
                    <span className="font-jb text-[10px] tracking-[0.14em] hidden sm:block" style={{ color: "rgba(245,239,225,0.28)" }}>
                      {simulation.data.n_simulations.toLocaleString()} Monte Carlo runs
                    </span>
                  )}
                </div>
                {simulation.data && <ChampionOdds teams={simulation.data.teams} />}
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
