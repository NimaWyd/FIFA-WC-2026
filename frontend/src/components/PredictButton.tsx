"use client";
import clsx from "clsx";

interface Props {
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
}

export default function PredictButton({ loading, disabled, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading}
      className={clsx(
        "w-full py-4 rounded-xl font-bold text-base tracking-wide transition-all duration-200",
        disabled || loading
          ? "bg-navy-700 text-slate-600 cursor-not-allowed"
          : "bg-fifa-blue text-white hover:bg-fifa-blue/90 shadow-[0_4px_20px_rgba(26,63,255,0.4)] hover:shadow-[0_4px_28px_rgba(26,63,255,0.6)]"
      )}
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          Predicting…
        </span>
      ) : (
        "Predict Outcome"
      )}
    </button>
  );
}
