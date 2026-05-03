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
        "w-full py-4 rounded-xl font-bold text-lg tracking-wide transition-all duration-200",
        disabled || loading
          ? "bg-slate-700 text-slate-500 cursor-not-allowed"
          : "bg-gradient-to-r from-gold-500 to-gold-400 text-navy-900 hover:from-gold-400 hover:to-gold-300 shadow-lg hover:shadow-gold-500/25"
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
        "Predict Match"
      )}
    </button>
  );
}
