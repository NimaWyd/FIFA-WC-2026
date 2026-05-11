interface Props {
  label: string;
  value: string | number | null | undefined;
  sub?: string;
}

export default function TeamStatCard({ label, value, sub }: Props) {
  return (
    <div className="bg-navy-700 border border-navy-600 rounded-xl p-4 flex flex-col gap-1 min-w-0">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider truncate">
        {label}
      </span>
      <span className="text-xl font-bold text-white truncate">{value ?? "—"}</span>
      {sub && <span className="text-xs text-slate-500 truncate">{sub}</span>}
    </div>
  );
}
