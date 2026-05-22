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
} from "@heroicons/react/24/solid";
import { fetchModelInfo } from "@/lib/api";
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

  useEffect(() => {
    fetchModelInfo().then(setModelInfo).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-navy-900 overflow-x-hidden">

      {/* ═══════════════════════════════════════════════════════
          HERO
      ══════════════════════════════════════════════════════ */}
      <section className="relative min-h-[60vh] md:min-h-[88vh] flex items-center overflow-hidden">
        {/* Atmospheric glows */}
        <div className="absolute inset-0 pointer-events-none">
          <div
            className="absolute top-1/2 right-0 w-[900px] h-[900px] rounded-full blur-[160px] -translate-y-1/2 translate-x-1/3"
            style={{ background: "rgba(245,200,66,0.055)" }}
          />
          <div
            className="absolute bottom-0 left-0 w-[500px] h-[500px] rounded-full blur-[120px]"
            style={{ background: "rgba(26,63,255,0.04)" }}
          />
        </div>

        <div className="relative max-w-4xl mx-auto px-4 py-10 md:py-24 w-full">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_430px] gap-14 items-center">

            {/* ── Text ── */}
            <motion.div
              initial={{ opacity: 0, y: 32 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.75, ease: "easeOut" }}
              className="flex flex-col gap-7"
            >
              {/* Eyebrow */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-px" style={{ background: "rgba(245,200,66,0.7)" }} />
                <span
                  className="text-[11px] font-semibold uppercase tracking-[0.3em]"
                  style={{ color: "rgba(245,200,66,0.8)" }}
                >
                  AI-Powered · FIFA World Cup 2026
                </span>
              </div>

              {/* Title */}
              <div className="leading-none">
                <div className="font-anton text-6xl sm:text-7xl xl:text-[88px] text-white tracking-wide">
                  INSIDE
                </div>
                <div
                  className="font-anton text-6xl sm:text-7xl xl:text-[88px] tracking-wide mt-1"
                  style={{ WebkitTextStroke: "1.5px rgba(245,200,66,0.85)", color: "transparent" }}
                >
                  THE MODEL
                </div>
              </div>

              {/* Description */}
              <p className="text-slate-400 text-[15px] leading-relaxed max-w-[420px]">
                An ensemble machine learning system trained on 49,000 international
                fixtures — delivering calibrated win probabilities, expected goals,
                and scoreline forecasts for every FIFA World Cup 2026 match.
              </p>

              {/* Hero stats */}
              <div className="flex items-center gap-7 pt-1">
                <div>
                  <div className="font-anton text-4xl text-white">49K+</div>
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">Training Fixtures</div>
                </div>
                <div className="w-px h-12 bg-navy-600" />
                <div>
                  <div className="font-anton text-4xl text-white">3</div>
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">Models Blended</div>
                </div>
                <div className="w-px h-12 bg-navy-600" />
                <div>
                  <div className="font-anton text-4xl text-white">48</div>
                  <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">Teams Modelled</div>
                </div>
              </div>
            </motion.div>

            {/* ── Trophy image ── */}
            <motion.div
              initial={{ opacity: 0, scale: 0.93, x: 24 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1], delay: 0.25 }}
              className="hidden lg:block"
            >
              <div
                className="relative h-[480px] rounded-2xl overflow-hidden"
                style={{ boxShadow: "0 0 100px rgba(245,200,66,0.09), 0 32px 80px rgba(0,0,0,0.55)" }}
              >
                <Image
                  src="/about/image1.webp"
                  alt="FIFA World Cup 2026 trophy and official Trionda match ball"
                  fill
                  className="object-cover"
                  priority
                />
                {/* Left gradient fade */}
                <div className="absolute inset-0 bg-gradient-to-l from-transparent via-navy-900/10 to-navy-900/65" />
                {/* Bottom fade */}
                <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-navy-900 to-transparent" />
                {/* Gold shimmer */}
                <div
                  className="absolute inset-0 opacity-[0.12]"
                  style={{ background: "linear-gradient(130deg, rgba(245,200,66,0.4) 0%, transparent 50%)" }}
                />
                {/* Top highlight */}
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />
              </div>
            </motion.div>
          </div>
        </div>

        {/* Section bottom fade */}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-navy-900 to-transparent" />
      </section>

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
                  className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider border border-slate-700/80 rounded-full px-3 py-0.5"
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
