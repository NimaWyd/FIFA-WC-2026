"use client";

import { motion } from "framer-motion";

interface Feature {
  feature: string;
  mean_abs_shap: number;
  label: string;
}

interface Props {
  features: Feature[];
}

const BAR_COLORS: Record<string, string> = {
  elo_win_prob: "#1a3fff",
};

function barColor(feature: string, index: number): string {
  if (feature in BAR_COLORS) return BAR_COLORS[feature];
  if (index < 4) return "#3b82f6";
  return "#64748b";
}

export default function FeatureImportanceChart({ features }: Props) {
  const max = Math.max(...features.map((f) => f.mean_abs_shap));

  return (
    <div className="flex flex-col gap-2.5">
      {features.map((f, i) => {
        const pct = (f.mean_abs_shap / max) * 100;
        const color = barColor(f.feature, i);
        return (
          <div key={f.feature} className="flex items-center gap-3">
            <span className="text-xs text-slate-400 w-44 flex-shrink-0 truncate text-right pr-1">
              {f.label}
            </span>
            <div className="flex-1 h-5 bg-navy-700 rounded-full overflow-hidden relative">
              <motion.div
                className="h-full rounded-full"
                style={{ backgroundColor: color }}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.6, delay: i * 0.05, ease: "easeOut" }}
              />
            </div>
            <span className="text-xs tabular-nums text-slate-500 w-12 flex-shrink-0">
              {f.mean_abs_shap.toFixed(3)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
