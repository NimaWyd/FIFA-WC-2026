"use client";

import { useEffect, useState, type FC, type SVGProps } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import {
  CpuChipIcon,
  ChartBarIcon,
  ShieldExclamationIcon,
  CodeBracketIcon,
  TrophyIcon,
  ArrowRightIcon,
  BeakerIcon,
  BoltIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  CircleStackIcon,
  UsersIcon,
} from "@heroicons/react/24/solid";
import { fetchModelInfo, fetchSimulation } from "@/lib/api";
import FeatureImportanceChart from "@/components/FeatureImportanceChart";
import type { ModelInfo } from "@/lib/types";

// ─── Data ───────────────────────────────────────────────────────────────────

const TOP_FEATURES = [
  { feature: "elo_win_prob",        mean_abs_shap: 0.196, label: "Elo Win Probability" },
  { feature: "elo_diff_home_away",  mean_abs_shap: 0.022, label: "Elo Difference" },
  { feature: "h2h_goal_diff",       mean_abs_shap: 0.020, label: "H2H Goal Difference" },
  { feature: "elo_diff_effective",  mean_abs_shap: 0.015, label: "Effective Elo Diff" },
  { feature: "home_defense_rw5",    mean_abs_shap: 0.014, label: "Home Defense Rating" },
  { feature: "away_adj_defense_w5", mean_abs_shap: 0.012, label: "Away Defense Rating" },
  { feature: "h2h_n_matches",       mean_abs_shap: 0.010, label: "H2H Match Count" },
  { feature: "home_adj_defense_w5", mean_abs_shap: 0.009, label: "Home Adj. Defense" },
  { feature: "neutral",             mean_abs_shap: 0.009, label: "Neutral Venue" },
  { feature: "away_elo_pre",        mean_abs_shap: 0.009, label: "Away Elo Rating" },
];


const PIPELINE_STEPS = [
  { num: "01", title: "Data Ingestion",       desc: "49,000+ international fixtures from 1993–2025, spanning WC, qualifiers, continental championships, and friendlies.", accent: "sky" },
  { num: "02", title: "Feature Engineering",  desc: "Elo ratings, rolling form windows, H2H records, defence ratings, rest days, and contextual flags built pre-match.", accent: "emerald" },
  { num: "03", title: "Chronological Split",  desc: "Train / val / test split preserving time order. No future information leaks into training features.", accent: "violet" },
  { num: "04", title: "Model Training",       desc: "XGBoost, Logistic Regression, and MLP trained independently on identical feature vectors with sample weighting.", accent: "orange" },
  { num: "05", title: "Ensemble Blending",    desc: "Per-class SLSQP weights optimised on the validation set. A dedicated draw submodel corrects systematic underestimation.", accent: "red" },
  { num: "06", title: "Calibration",          desc: "Per-class OvR isotonic calibrators ensure stated 60% confidence is empirically correct ~60% of the time.", accent: "yellow" },
] as const;

type AccentKey = (typeof PIPELINE_STEPS)[number]["accent"];

const ACCENTS: Record<AccentKey, { text: string; border: string; topBar: string }> = {
  sky:     { text: "text-sky-400",     border: "border-sky-400/25",     topBar: "bg-sky-400"     },
  emerald: { text: "text-emerald-400", border: "border-emerald-400/25", topBar: "bg-emerald-400" },
  violet:  { text: "text-violet-400",  border: "border-violet-400/25",  topBar: "bg-violet-400"  },
  orange:  { text: "text-orange-400",  border: "border-orange-400/25",  topBar: "bg-orange-400"  },
  red:     { text: "text-red-400",     border: "border-red-400/25",     topBar: "bg-red-400"     },
  yellow:  { text: "text-yellow-400",  border: "border-yellow-400/25",  topBar: "bg-yellow-400"  },
};

const ENSEMBLE_MODELS = [
  { name: "XGBoost",              borderTop: "border-t-green-400",  text: "text-green-400",  desc: "Gradient-boosted decision trees. Handles non-linear interactions and class imbalance. The dominant backbone of the ensemble." },
  { name: "Logistic Regression",  borderTop: "border-t-sky-400",    text: "text-sky-400",    desc: "Linear baseline classifier. Highly interpretable, provides stable, well-calibrated probability estimates as an anchor." },
  { name: "MLP",                  borderTop: "border-t-purple-400", text: "text-purple-400", desc: "Multi-layer perceptron. Captures deep feature interactions and complex patterns that tree-based models miss." },
];

type HeroIcon = FC<SVGProps<SVGSVGElement> & { className?: string }>;

interface GlossaryItem { term: string; icon: HeroIcon; color: string; definition: string; }
const GLOSSARY: GlossaryItem[] = [
  { term: "Win Probability",      icon: ChartBarIcon,    color: "text-sky-400",    definition: "P(home win), P(draw), P(away win) from the ensemble model. The three values always sum to 1.0." },
  { term: "Predicted Score",      icon: BoltIcon,        color: "text-yellow-400", definition: "Most-likely scoreline from a team-dependent Poisson model whose expected goals are calibrated to reproduce the ensemble's exact outcome probabilities." },
  { term: "Expected Goals (xG)",  icon: BeakerIcon,      color: "text-emerald-400",definition: "The Poisson lambda — the mean goals each team is expected to score. Fractional is normal: xG 1.4 means between 1 and 2 goals on average." },
  { term: "Confidence",           icon: CheckCircleIcon, color: "text-green-400",  definition: "The highest of the three outcome probabilities. Above ~55% is considered meaningful; below 40% the match is too close to call reliably." },
];

const LIMITATIONS = [
  "Squad injuries and suspensions are not modelled — the system uses historical team-level performance only.",
  "Individual player ratings are not used. A squad-strength feature is planned but not yet implemented.",
  "Predictions are probabilistic — upsets are expected and statistically normal. A 75% favourite still loses 1 in 4 times.",
  "The model trains on matches from 1993 onwards. Very new national team programs may have limited training history.",
];

const TECH_STACK = [
  { category: "ML & Data",  items: ["Python", "XGBoost", "scikit-learn", "SciPy", "NumPy", "pandas", "SHAP"], cat: "text-green-400",  pill: "bg-green-400/10 border-green-400/20 text-green-300" },
  { category: "API",        items: ["FastAPI", "Uvicorn", "Pydantic", "joblib"],                               cat: "text-sky-400",    pill: "bg-sky-400/10 border-sky-400/20 text-sky-300"       },
  { category: "Frontend",   items: ["Next.js 14", "TypeScript", "Tailwind CSS", "Framer Motion", "Recharts"], cat: "text-purple-400", pill: "bg-purple-400/10 border-purple-400/20 text-purple-300" },
];

const CREATORS = [
  {
    name: "Nima Abbasi",
    title: "Computer Science Student at Western University",
    initial: "N",
    photo: "/about/nima.jpeg",
    avatarFrom: "#f5c842",
    avatarTo: "#f59e0b",
    initialColor: "#000",
    github: "https://github.com/NimaWyd",
    linkedin: "https://linkedin.com/in/nima-abbasi2004?_l=en_US",
  },
  {
    name: "Tareq Kurdiah",
    title: "Computer Science Student at Western University",
    initial: "T",
    photo: "/about/tareq.jpeg",
    avatarFrom: "#3b82f6",
    avatarTo: "#1d4ed8",
    initialColor: "#fff",
    github: "https://github.com/tareqrwk",
    linkedin: "https://linkedin.com/in/tareq-kurdiah?_l=en_US",
  },
] as const;

const CHAMPION_COLORS = ["#f5c842", "#38bdf8", "#10b981"];

// ─── Animation ──────────────────────────────────────────────────────────────

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1, delayChildren: 0.04 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.55, ease: "easeOut" as const } },
};

// ─── Component ──────────────────────────────────────────────────────────────

export default function AboutPage() {
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [championOdds, setChampionOdds] = useState<{ team: string; pct: number; color: string }[] | null>(null);

  useEffect(() => {
    fetchModelInfo().then(setModelInfo).catch(() => {});
    fetchSimulation()
      .then((sim) => {
        const top3 = [...sim.teams]
          .sort((a, b) => b.champion - a.champion)
          .slice(0, 3)
          .map((t, i) => ({ team: t.team, pct: Math.round(t.champion * 100), color: CHAMPION_COLORS[i] }));
        setChampionOdds(top3);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-navy-900 overflow-x-hidden">

      {/* ═══════════════════════════════════════════════════════
          FULL-BLEED PAGE HERO IMAGE
      ══════════════════════════════════════════════════════ */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.1, ease: "easeOut" }}
        className="relative w-full overflow-hidden"
      >
        <Image
          src="/about/hero.png"
          alt="FIFA World Cup 2026 Predictor"
          width={1536}
          height={1024}
          className="w-full h-auto"
          priority
        />
        {/* Bottom fade into page background */}
        <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-navy-900 to-transparent" />
        {/* Subtle top darken */}
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-navy-900/60 to-transparent" />
        {/* Side vignette */}
        <div className="absolute inset-0 bg-gradient-to-r from-navy-900/30 via-transparent to-navy-900/30" />
      </motion.div>

      {/* ═══════════════════════════════════════════════════════
          WC 2026 CONTEXT — STAT STRIP
      ══════════════════════════════════════════════════════ */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.4 }}
          className="border-t border-b border-navy-600 py-6 flex flex-col gap-4"
        >
          {/* Stats row */}
          <div className="flex items-center justify-around gap-4 flex-wrap">
            {[
              { value: "48",       label: "Teams"        },
              { value: "3",        label: "Host Nations"  },
              { value: "104",      label: "Matches"       },
              { value: "June–July",  label: "2026"          },
            ].map(({ value, label }, i, arr) => (
              <div key={label} className="flex items-center gap-4">
                <div className="text-center">
                  <div className="font-anton text-4xl sm:text-5xl" style={{ color: "#f5c842" }}>{value}</div>
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">{label}</div>
                </div>
                {i < arr.length - 1 && <div className="w-px h-10 bg-navy-600 hidden sm:block" />}
              </div>
            ))}
          </div>
          {/* Host badges */}
          <div className="flex items-center justify-center gap-6 flex-wrap">
            {[
              { iso: "us", name: "USA"    },
              { iso: "ca", name: "Canada" },
              { iso: "mx", name: "Mexico" },
            ].map(({ iso, name }) => (
              <div key={name} className="flex flex-col items-center gap-1.5">
                <span className={`fi fi-${iso} rounded`} style={{ fontSize: "36px", lineHeight: 1 }} />
                <span className="text-[11px] font-semibold text-sky-300 uppercase tracking-widest">{name}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* ═══════════════════════════════════════════════════════
          STADIUM FULL-BLEED BANNER
      ══════════════════════════════════════════════════════ */}
      <div className="relative h-64 sm:h-80 overflow-hidden">
        <Image
          src="/about/image2.jpeg"
          alt="FIFA World Cup 2026 host stadium"
          fill
          className="object-cover object-center"
          sizes="100vw"
        />
        {/* Directional overlay */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to right, rgba(9,11,20,0.97) 0%, rgba(9,11,20,0.78) 40%, rgba(9,11,20,0.40) 75%, rgba(9,11,20,0.15) 100%)",
          }}
        />
        {/* Bottom edge blend */}
        <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-navy-900 to-transparent" />
        <div className="absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-navy-900 to-transparent" />

        <div className="absolute inset-0 flex items-center">
          <motion.div
            initial={{ opacity: 0, x: -28 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.75 }}
            viewport={{ once: true }}
            className="max-w-4xl mx-auto px-4 w-full"
          >
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-[0.25em] mb-2">
              Training dataset
            </div>
            <div
              className="font-anton text-6xl sm:text-8xl leading-none"
              style={{
                color: "rgba(245,200,66,1)",
                textShadow: "0 0 80px rgba(245,200,66,0.5), 0 0 160px rgba(245,200,66,0.2)",
              }}
            >
              49,000+
            </div>
            <div className="font-anton text-xl sm:text-3xl text-slate-400 mt-2 leading-none tracking-wide">
              INTERNATIONAL FIXTURES ANALYSED
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              {["World Cup", "Qualifiers", "Continental Championships", "Nations League", "Friendlies"].map((label) => (
                <span
                  key={label}
                  className="text-[10px] font-semibold text-slate-200 uppercase tracking-wider border border-slate-400/50 rounded-full px-3 py-0.5 bg-black/30 backdrop-blur-sm"
                >
                  {label}
                </span>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════
          MAIN CONTENT
      ══════════════════════════════════════════════════════ */}
      <div className="max-w-4xl mx-auto px-4 py-14 flex flex-col gap-12">

        {/* ── HOW IT WORKS ── */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.05 }}
          className="flex flex-col gap-6"
        >
          <motion.div variants={fadeUp}>
            <div className="flex items-center gap-2 mb-1">
              <CpuChipIcon className="h-4 w-4 text-fifa-blue-light" />
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">How It Works</span>
            </div>
            <p className="text-slate-500 text-sm">From raw match history to calibrated predictions — the full 6-step pipeline.</p>
          </motion.div>

          {/* Pipeline grid */}
          <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {PIPELINE_STEPS.map((step) => {
              const s = ACCENTS[step.accent];
              return (
                <div
                  key={step.num}
                  className={`relative bg-navy-800 border ${s.border} rounded-xl p-4 flex flex-col gap-2 overflow-hidden`}
                >
                  {/* Accent top bar */}
                  <div className={`absolute inset-x-0 top-0 h-0.5 ${s.topBar} opacity-50`} />
                  <span className={`font-jb text-[10px] font-bold ${s.text} opacity-50 tracking-wider`}>{step.num}</span>
                  <span className={`text-sm font-bold ${s.text}`}>{step.title}</span>
                  <span className="text-[11px] text-slate-500 leading-relaxed">{step.desc}</span>
                </div>
              );
            })}
          </motion.div>

          {/* Ensemble architecture */}
          <motion.div variants={fadeUp} className="bg-navy-800 border border-navy-600 rounded-2xl p-6 flex flex-col gap-5">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Ensemble Architecture
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {ENSEMBLE_MODELS.map((m) => (
                <div
                  key={m.name}
                  className={`bg-navy-700 border border-navy-600 border-t-2 ${m.borderTop} rounded-xl p-4 flex flex-col gap-2`}
                >
                  <span className={`text-sm font-bold ${m.text}`}>{m.name}</span>
                  <span className="text-[11px] text-slate-400 leading-relaxed">{m.desc}</span>
                </div>
              ))}
            </div>

            {/* Merge arrow */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-navy-600" />
              <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                <ArrowRightIcon className="h-3 w-3" />
                <span>SLSQP optimised blending + draw submodel</span>
                <ArrowRightIcon className="h-3 w-3" />
              </div>
              <div className="flex-1 h-px bg-navy-600" />
            </div>

            {/* Output */}
            <div
              className="rounded-xl border border-fifa-blue/25 border-t-2 border-t-fifa-blue p-4 text-center"
              style={{ background: "rgba(26,63,255,0.04)" }}
            >
              <div className="text-sm font-bold text-fifa-blue-light mb-1">Ensemble Model</div>
              <div className="text-[11px] text-slate-400 max-w-md mx-auto leading-relaxed">
                Per-class weights optimised on the held-out validation set.
                Draw probability corrected via a dedicated binary logistic submodel.
                Output isotonically calibrated per class.
              </div>
            </div>
          </motion.div>
        </motion.section>

        {/* ── MONTE CARLO SIMULATION ── */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          className="flex flex-col gap-5"
        >
          <motion.div variants={fadeUp}>
            <div className="flex items-center gap-2 mb-1">
              <ArrowPathIcon className="h-4 w-4 text-sky-400" />
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Monte Carlo Simulation</span>
            </div>
            <p className="text-slate-500 text-sm">We run the full 48-team tournament 5,000 times. Each run draws match outcomes from the model&apos;s probability distributions and tracks every team&apos;s path. Final win chances are frequencies across all runs.</p>
          </motion.div>

          <motion.div variants={fadeUp} className="bg-navy-800 border border-navy-600 rounded-2xl p-6 flex flex-col gap-5">
            {/* Headline stats */}
            <div className="grid grid-cols-2 divide-x divide-navy-600">
              <div className="pr-6 flex flex-col gap-1">
                <span className="font-anton text-5xl" style={{ color: "#f5c842", textShadow: "0 0 30px rgba(245,200,66,0.35)" }}>5,000</span>
                <span className="text-xs font-semibold text-slate-400">Simulations per request</span>
                <span className="text-[10px] text-slate-600">Full tournament, group → final</span>
              </div>
              <div className="pl-6 flex flex-col gap-1">
                <span className="font-anton text-5xl text-sky-400">520K+</span>
                <span className="text-xs font-semibold text-slate-400">Match outcomes modelled</span>
                <span className="text-[10px] text-slate-600">5,000 runs × 104 matches</span>
              </div>
            </div>

            {/* Champion probability bars */}
            <div className="border-t border-navy-600 pt-4 flex flex-col gap-3">
              <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Champion probability · top 3
              </div>
              {championOdds === null ? (
                <div className="text-[11px] text-slate-500 italic">Loading simulation…</div>
              ) : (
                championOdds.map(({ team, pct, color }) => (
                  <div key={team} className="flex items-center gap-3">
                    <span className="text-sm text-slate-300 w-20 flex-shrink-0 truncate">{team}</span>
                    <div className="flex-1 bg-navy-700 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full"
                        style={{ width: `${pct}%`, background: color }}
                      />
                    </div>
                    <span className="text-sm font-semibold w-8 text-right" style={{ color }}>{pct}%</span>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </motion.section>

        {/* ── ACCURACY METRICS ── */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          className="flex flex-col gap-5"
        >
          <motion.div variants={fadeUp} className="flex items-center gap-2">
            <ChartBarIcon className="h-4 w-4" style={{ color: "rgba(245,200,66,0.8)" }} />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Backtest Accuracy</span>
          </motion.div>

          <motion.div variants={fadeUp} className="bg-navy-800 border border-navy-600 rounded-2xl overflow-hidden">
            {/* Header bar */}
            <div className="px-6 py-3.5 border-b border-navy-600 bg-navy-700/40">
              <span className="text-[11px] text-slate-500">
                Chronological backtest
                {modelInfo?.accuracy_metrics ? ` · ${modelInfo.accuracy_metrics.test_rows.toLocaleString()}-match held-out test set` : ""}
                {" "}· Isotonic calibration applied · 3-class H / D / A
              </span>
            </div>

            {/* Stat cells */}
            <div className="grid grid-cols-3 divide-x divide-navy-600">
              <div className="p-6 sm:p-8 flex flex-col items-center gap-2">
                <span
                  className="font-anton text-5xl sm:text-6xl"
                  style={{ color: "rgba(245,200,66,1)", textShadow: "0 0 30px rgba(245,200,66,0.4)" }}
                >
                  {modelInfo?.accuracy_metrics
                    ? `${(modelInfo.accuracy_metrics.accuracy * 100).toFixed(0)}%`
                    : "—"}
                </span>
                <span className="text-xs font-semibold text-slate-400">Test Accuracy</span>
                <span className="text-[10px] text-slate-600 text-center">Random baseline ~33%</span>
              </div>
              <div className="p-6 sm:p-8 flex flex-col items-center gap-2">
                <span className="font-anton text-5xl sm:text-6xl text-sky-400">
                  {modelInfo?.accuracy_metrics
                    ? modelInfo.accuracy_metrics.brier_score.toFixed(3)
                    : "—"}
                </span>
                <span className="text-xs font-semibold text-slate-400">Brier Score</span>
                <span className="text-[10px] text-slate-600">Lower is better</span>
              </div>
              <div className="p-6 sm:p-8 flex flex-col items-center gap-2">
                <span className="font-anton text-5xl sm:text-6xl text-purple-400">
                  {modelInfo?.accuracy_metrics
                    ? modelInfo.accuracy_metrics.log_loss.toFixed(2)
                    : "—"}
                </span>
                <span className="text-xs font-semibold text-slate-400">Log Loss</span>
                <span className="text-[10px] text-slate-600">Lower is better</span>
              </div>
            </div>
          </motion.div>
        </motion.section>

        {/* ── SHAP FEATURE IMPORTANCE ── */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          className="flex flex-col gap-5"
        >
          <motion.div variants={fadeUp}>
            <div className="flex items-center gap-2 mb-1">
              <BeakerIcon className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Feature Importance (SHAP)</span>
            </div>
            <p className="text-xs text-slate-500">Mean absolute SHAP value across 161 test samples — what actually drives the prediction.</p>
          </motion.div>

          <motion.div variants={fadeUp} className="bg-navy-800 border border-navy-600 rounded-2xl p-6 flex flex-col gap-5">
            {/* Dominant-signal callout */}
            <div className="bg-fifa-blue/10 border border-fifa-blue/25 rounded-xl px-4 py-3 flex flex-col gap-1">
              <span className="text-[10px] font-bold text-fifa-blue-light uppercase tracking-wider">Dominant Signal</span>
              <p className="text-sm text-slate-300 leading-relaxed">
                <span className="text-white font-semibold">Elo Win Probability</span> outweighs every
                other feature by <span className="text-white font-semibold">~8×</span> (SHAP 0.196 vs
                0.022 for the next feature). Defence ratings are the next meaningful signal.
                FIFA rank, streaks, and competition category are near-zero contributors.
              </p>
            </div>
            <FeatureImportanceChart features={TOP_FEATURES} />
          </motion.div>
        </motion.section>

        {/* ── DATA SOURCES + SQUAD TRACKING ── */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          className="grid grid-cols-1 sm:grid-cols-2 gap-5"
        >
          {/* Match Data */}
          <motion.div variants={fadeUp} className="bg-navy-800 border border-navy-600 rounded-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <CircleStackIcon className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Match Data</span>
            </div>
            <div>
              <div className="font-anton text-3xl text-white">49,000+</div>
              <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">Historical fixtures</div>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed flex-1">
              International results from 1993–2025 spanning World Cups, qualifiers, continental championships, and friendlies.
            </p>
            <span className="self-start text-[11px] font-semibold px-2.5 py-0.5 rounded-full border bg-emerald-400/10 border-emerald-400/20 text-emerald-300">
              football-data.org
            </span>
          </motion.div>

          {/* Live Squads */}
          <motion.div variants={fadeUp} className="bg-navy-800 border border-navy-600 rounded-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <UsersIcon className="h-4 w-4" style={{ color: "rgba(245,200,66,0.8)" }} />
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Live Squads</span>
            </div>
            <div>
              <div className="font-anton text-3xl text-white">Official</div>
              <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">WC 2026 rosters</div>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed flex-1">
              Player names, ages, clubs, and portraits updated as each nation announces their final 26-man squad.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {["SofaScore", "ESPN", "FotMob"].map((src) => (
                <span key={src} className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full border bg-yellow-400/10 border-yellow-400/20 text-yellow-300">
                  {src}
                </span>
              ))}
            </div>
          </motion.div>
        </motion.section>

        {/* ── GLOSSARY ── */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          className="flex flex-col gap-5"
        >
          <motion.div variants={fadeUp} className="flex items-center gap-2">
            <TrophyIcon className="h-4 w-4" style={{ color: "rgba(245,200,66,0.7)" }} />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">What Each Output Means</span>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {GLOSSARY.map(({ term, icon: Icon, color, definition }) => (
              <motion.div
                key={term}
                variants={fadeUp}
                className="bg-navy-800 border border-navy-600 rounded-xl p-5 flex flex-col gap-3"
              >
                <div className="flex items-center gap-2.5">
                  <div className={`p-1.5 rounded-lg bg-navy-700 border border-navy-600`}>
                    <Icon className={`h-3.5 w-3.5 ${color}`} />
                  </div>
                  <span className="text-sm font-bold text-white">{term}</span>
                </div>
                <span className="text-sm text-slate-400 leading-relaxed">{definition}</span>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* ── LIMITATIONS + TECH STACK ── */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.08 }}
          className="grid grid-cols-1 sm:grid-cols-2 gap-5"
        >
          {/* Limitations */}
          <motion.div variants={fadeUp} className="bg-navy-800 border border-navy-600 rounded-2xl p-6 flex flex-col gap-5">
            <div className="flex items-center gap-2">
              <ShieldExclamationIcon className="h-4 w-4 text-orange-400" />
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Limitations</span>
            </div>
            <ul className="flex flex-col gap-4">
              {LIMITATIONS.map((text, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="flex-shrink-0 font-jb text-[10px] font-bold text-orange-400/50 mt-0.5 w-5 text-right">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="text-sm text-slate-400 leading-relaxed">{text}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Tech Stack */}
          <motion.div variants={fadeUp} className="bg-navy-800 border border-navy-600 rounded-2xl p-6 flex flex-col gap-5">
            <div className="flex items-center gap-2">
              <CodeBracketIcon className="h-4 w-4 text-purple-400" />
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Tech Stack</span>
            </div>
            <div className="flex flex-col gap-5">
              {TECH_STACK.map(({ category, items, cat, pill }) => (
                <div key={category}>
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${cat} block mb-2`}>{category}</span>
                  <div className="flex flex-wrap gap-1.5">
                    {items.map((item) => (
                      <span key={item} className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${pill}`}>
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.section>

        {/* ── BUILT BY ── */}
        <motion.section
          variants={stagger}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          className="flex flex-col gap-5"
        >
          <motion.div variants={fadeUp} className="flex items-center gap-2">
            <UsersIcon className="h-4 w-4" style={{ color: "rgba(245,200,66,0.7)" }} />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Built by</span>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 max-w-2xl mx-auto w-full">
            {CREATORS.map((c, i) => {
              const accent = i === 0
                ? { glow: "rgba(245,200,66,0.18)", border: "rgba(245,200,66,0.35)", tag: "#f5c842" }
                : { glow: "rgba(59,130,246,0.18)",  border: "rgba(59,130,246,0.35)",  tag: "#3b82f6"  };
              return (
                <motion.div
                  key={c.name}
                  variants={fadeUp}
                  whileHover={{ y: -4, transition: { duration: 0.2 } }}
                  className="relative rounded-2xl overflow-hidden flex flex-col"
                  style={{
                    background: "rgba(15,19,36,0.95)",
                    border: `1px solid ${accent.border}`,
                    boxShadow: `0 0 40px ${accent.glow}, 0 8px 32px rgba(0,0,0,0.5)`,
                  }}
                >
                  {/* Photo */}
                  <div className="relative w-full overflow-hidden">
                    <Image
                      src={c.photo}
                      alt={c.name}
                      width={600}
                      height={600}
                      className="w-full h-auto block"
                      sizes="(max-width: 640px) 50vw, 300px"
                    />
                    {/* Bottom gradient */}
                    <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#0f1324] to-transparent" />
                    {/* Top accent bar */}
                    <div className="absolute inset-x-0 top-0 h-0.5" style={{ background: accent.tag }} />
                    {/* Role badge */}
                    <div
                      className="absolute top-4 left-4 text-[9px] font-bold uppercase tracking-[0.25em] px-2.5 py-1 rounded-full"
                      style={{ background: `${accent.tag}55`, border: `1px solid ${accent.tag}cc`, color: "#fff" }}
                    >
                      Creator
                    </div>
                  </div>

                  {/* Info */}
                  <div className="px-6 py-5 flex flex-col gap-4">
                    <div>
                      <div className="font-anton text-2xl text-white tracking-wide leading-tight">{c.name}</div>
                      <div className="text-[11px] text-slate-500 mt-1">{c.title}</div>
                    </div>

                    {/* Links */}
                    <div className="flex gap-3">
                      <a
                        href={c.github}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 flex-1 justify-center py-2 rounded-xl text-[11px] font-semibold text-slate-300 hover:text-white transition-all"
                        style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = accent.border)}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)")}
                      >
                        {/* GitHub icon */}
                        <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
                          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.44 9.8 8.2 11.38.6.1.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.08-.74.08-.73.08-.73 1.2.09 1.83 1.23 1.83 1.23 1.07 1.83 2.8 1.3 3.48 1 .1-.78.42-1.31.76-1.61-2.67-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.14-.3-.54-1.52.1-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 3-.4c1.02 0 2.04.13 3 .4 2.28-1.55 3.29-1.23 3.29-1.23.64 1.66.24 2.88.12 3.18.77.84 1.23 1.91 1.23 3.22 0 4.61-2.81 5.63-5.48 5.92.43.37.81 1.1.81 2.22v3.29c0 .32.22.69.83.57C20.57 21.8 24 17.3 24 12c0-6.63-5.37-12-12-12z"/>
                        </svg>
                        GitHub
                      </a>
                      <a
                        href={c.linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 flex-1 justify-center py-2 rounded-xl text-[11px] font-semibold transition-all"
                        style={{ background: `${accent.tag}18`, border: `1px solid ${accent.border}`, color: accent.tag }}
                        onMouseEnter={e => (e.currentTarget.style.background = `${accent.tag}28`)}
                        onMouseLeave={e => (e.currentTarget.style.background = `${accent.tag}18`)}
                      >
                        {/* LinkedIn icon */}
                        <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
                          <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.36V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/>
                        </svg>
                        LinkedIn
                      </a>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.section>

        {/* ── GITHUB / MODEL INFO ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.55 }}
          className="rounded-2xl border border-navy-600 bg-navy-800 p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-5"
        >
          <div className="flex flex-col gap-1.5">
            <div className="text-base font-bold text-white">Open Source</div>
            <div className="text-sm text-slate-400 max-w-sm">
              Full ML pipeline and frontend source code publicly available.
            </div>
            {modelInfo && (
              <div className="text-xs text-slate-500 mt-0.5">
                Model type: <span className="text-slate-400">{modelInfo.model_type}</span>
                {modelInfo.training_cutoff && (
                  <> · Training cutoff: <span className="text-slate-400">{modelInfo.training_cutoff}</span></>
                )}
              </div>
            )}
          </div>
          <a
            href="https://github.com/NimaWyd/FIFA-WC-2026"
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 self-start sm:self-auto flex items-center gap-2 px-6 py-3 rounded-xl border border-navy-600 bg-navy-700 text-sm font-semibold text-slate-300 hover:text-white hover:border-slate-500 hover:bg-navy-600 transition-all cursor-pointer"
          >
            View on GitHub
            <ArrowRightIcon className="h-4 w-4" />
          </a>
        </motion.div>

      </div>
    </div>
  );
}
