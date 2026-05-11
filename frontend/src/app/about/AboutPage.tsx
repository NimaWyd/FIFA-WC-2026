"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { fetchModelInfo } from "@/lib/api";
import FeatureImportanceChart from "@/components/FeatureImportanceChart";
import TeamStatCard from "@/components/TeamStatCard";
import type { ModelInfo } from "@/lib/types";

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, delay: i * 0.08, ease: "easeOut" as const },
  }),
};

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

const ACCURACY_METRICS = {
  accuracy: 0.36,
  brier_score: 0.766,
  log_loss: 2.29,
  test_rows: 25,
};

interface GlossaryItem {
  term: string;
  definition: string;
}

const GLOSSARY: GlossaryItem[] = [
  {
    term: "Win probability",
    definition:
      "P(home win), P(draw), P(away win) from the ensemble model. Three probabilities always sum to 1.",
  },
  {
    term: "Predicted score",
    definition:
      "The most likely scoreline from a team-dependent Poisson model whose lambdas are calibrated to exactly match the ensemble outcome probabilities.",
  },
  {
    term: "Expected goals (xG)",
    definition:
      "The Poisson lambda values: the mean number of goals each team is expected to score. Fractional numbers are normal — e.g. xG 1.4 means between 1 and 2 goals on average.",
  },
  {
    term: "Confidence",
    definition:
      "The highest of the three outcome probabilities. Values above ~55% are considered meaningful; below 40% the match is too close to call reliably.",
  },
];

const LIMITATIONS = [
  "Squad injuries and suspensions are not accounted for — the model uses historical team-level data only.",
  "Player ratings are not used. A squad-strength feature is planned but not yet implemented.",
  "Predictions are probabilistic — upsets are expected and normal. Even a 75% favourite loses 1 in 4 times.",
  "The model is trained on matches from 1993 onwards. Very new national team programs may have limited history.",
];

export default function AboutPage() {
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);

  useEffect(() => {
    fetchModelInfo()
      .then(setModelInfo)
      .catch(() => {});
  }, []);

  return (
    <main className="min-h-screen bg-navy-900">
      <div className="max-w-4xl mx-auto px-4 py-10 flex flex-col gap-6">
        {/* Page header */}
        <motion.div custom={0} initial="hidden" animate="visible" variants={cardVariants}>
          <h1 className="text-2xl font-bold text-white">About the Model</h1>
          <p className="text-slate-400 text-sm mt-1">
            How the AI prediction engine works, what each output means, and its known limitations.
          </p>
        </motion.div>

        {/* ── How it works ── */}
        <motion.div
          custom={1} initial="hidden" animate="visible" variants={cardVariants}
          className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-4"
        >
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            How It Works
          </h2>

          <div className="flex flex-col gap-3 text-sm text-slate-300 leading-relaxed">
            <p>
              The predictor is an{" "}
              <span className="text-white font-semibold">ensemble model</span> — it blends three
              classifiers (XGBoost, Logistic Regression, and a Multi-Layer Perceptron) using
              per-class SLSQP weights optimised on a held-out validation set. A dedicated binary
              draw submodel corrects the ensemble&apos;s known tendency to underestimate draws.
            </p>

            <p>
              <span className="text-white font-semibold">Training data</span> covers international
              football matches from 1993 to present — roughly 49,000 fixtures. Pre-1993 data is
              excluded because the pre-modern game is structurally different and produces degenerate
              gradients during XGBoost training. The dataset includes World Cup qualifiers,
              continental championships, Nations Leagues, and friendlies.
            </p>

            <p>
              The train/val/test split is strictly{" "}
              <span className="text-white font-semibold">chronological</span>. No future data leaks
              into training — all features (Elo ratings, rolling form, head-to-head records) are
              computed from matches that occurred{" "}
              <span className="italic">before</span> the match being predicted.
            </p>

            <p>
              Win probabilities are{" "}
              <span className="text-white font-semibold">isotonically calibrated</span> per class
              (home/draw/away) to ensure the model&apos;s stated 60% is actually correct 60% of the
              time. Scorelines are generated from a team-dependent Poisson model whose expected
              goals are back-solved to reproduce the ensemble&apos;s exact outcome probabilities.
            </p>
          </div>
        </motion.div>

        {/* ── Feature importance ── */}
        <motion.div
          custom={2} initial="hidden" animate="visible" variants={cardVariants}
          className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
              Feature Importance (SHAP)
            </h2>
            <p className="text-xs text-slate-500">Mean absolute SHAP value across 161 samples</p>
          </div>

          {/* Callout for dominant feature */}
          <div className="bg-fifa-blue/10 border border-fifa-blue/30 rounded-xl px-4 py-3 flex flex-col gap-1">
            <span className="text-xs font-semibold text-fifa-blue-light uppercase tracking-wider">
              Top signal
            </span>
            <p className="text-sm text-slate-300">
              <span className="text-white font-semibold">Elo win probability</span> dominates all
              other features by roughly <span className="text-white font-semibold">8×</span>{" "}
              (SHAP 0.196 vs 0.022 for the next feature). Defence ratings are the next meaningful
              signal. Streak features, FIFA rank, and competition category are near-zero contributors.
            </p>
          </div>

          <FeatureImportanceChart features={TOP_FEATURES} />
        </motion.div>

        {/* ── Accuracy metrics ── */}
        <motion.div
          custom={3} initial="hidden" animate="visible" variants={cardVariants}
          className="flex flex-col gap-3"
        >
          <div>
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
              Backtest Accuracy
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Chronological backtest · {ACCURACY_METRICS.test_rows}-match test set ·
              Isotonic calibration applied
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <TeamStatCard
              label="Accuracy"
              value={`${(ACCURACY_METRICS.accuracy * 100).toFixed(0)}%`}
              sub="3-class (H/D/A)"
            />
            <TeamStatCard
              label="Brier Score"
              value={ACCURACY_METRICS.brier_score.toFixed(3)}
              sub="Lower is better"
            />
            <TeamStatCard
              label="Log Loss"
              value={ACCURACY_METRICS.log_loss.toFixed(2)}
              sub="Lower is better"
            />
          </div>
        </motion.div>

        {/* ── Glossary ── */}
        <motion.div
          custom={4} initial="hidden" animate="visible" variants={cardVariants}
          className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-4"
        >
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            What Each Output Means
          </h2>
          <div className="flex flex-col divide-y divide-navy-600">
            {GLOSSARY.map(({ term, definition }) => (
              <div key={term} className="py-3 first:pt-0 last:pb-0 flex flex-col gap-1">
                <span className="text-sm font-semibold text-white">{term}</span>
                <span className="text-sm text-slate-400">{definition}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* ── Limitations ── */}
        <motion.div
          custom={5} initial="hidden" animate="visible" variants={cardVariants}
          className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-4"
        >
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            Limitations
          </h2>
          <ul className="flex flex-col gap-2">
            {LIMITATIONS.map((item, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-slate-400">
                <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-slate-600 mt-1.5" />
                {item}
              </li>
            ))}
          </ul>
        </motion.div>

        {/* ── Footer / links ── */}
        <motion.div
          custom={6} initial="hidden" animate="visible" variants={cardVariants}
          className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-4"
        >
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            Tech Stack & Links
          </h2>
          <div className="flex flex-col gap-2 text-sm text-slate-400">
            <p>
              <span className="text-slate-300 font-medium">Backend:</span> Python · FastAPI ·
              XGBoost · scikit-learn · SciPy
            </p>
            <p>
              <span className="text-slate-300 font-medium">Frontend:</span> Next.js 14 ·
              TypeScript · Tailwind CSS · Framer Motion
            </p>
            {modelInfo && (
              <p className="text-slate-500 text-xs mt-1">
                Model last retrained:{" "}
                <span className="text-slate-400">{modelInfo.training_cutoff}</span> ·
                Type: <span className="text-slate-400">{modelInfo.model_type}</span>
              </p>
            )}
            <a
              href="https://github.com/NimaWyd/FIFA-WC-2026"
              target="_blank"
              rel="noopener noreferrer"
              className="text-fifa-blue-light hover:underline mt-1 w-fit"
            >
              View source on GitHub →
            </a>
          </div>
        </motion.div>
      </div>
    </main>
  );
}
