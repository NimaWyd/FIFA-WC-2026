"use client";
import clsx from "clsx";
import type { Scoreline } from "@/lib/types";

interface Props {
  scorelines: Scoreline[];
}

export default function ScorelineGrid({ scorelines }: Props) {
  if (!scorelines || scorelines.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Top Scorelines</h3>
        <p className="text-slate-500 text-sm">No scoreline probabilities available.</p>
      </div>
    );
  }

  const max = Math.max(...scorelines.map((s) => s.probability));
  const safeMax = max > 0 ? max : 1;

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Top Scorelines</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
        {scorelines.map((s, i) => (
          <div
            key={s.scoreline}
            className={clsx(
              "flex flex-col items-center justify-center rounded-xl py-4 px-2 bg-navy-700 border",
              i === 0 ? "border-fifa-blue" : "border-navy-600"
            )}
          >
            <span className={clsx("text-2xl font-bold", i === 0 ? "text-fifa-blue-light" : "text-white")}>
              {s.scoreline}
            </span>
            <span className="text-xs text-slate-400 mt-1">{(s.probability * 100).toFixed(1)}%</span>
            <div className="w-full bg-navy-600 rounded-full h-1 mt-2">
              <div
                className={clsx("h-1 rounded-full", i === 0 ? "bg-fifa-blue" : "bg-slate-500")}
                style={{ width: `${(s.probability / safeMax) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
