import type { PredictResponse } from "@/lib/types";

interface Props {
  result: PredictResponse;
}

export default function MetadataBadge({ result }: Props) {
  const modelType = result.metadata?.model_type as string | undefined;
  const trainingCutoff = result.metadata?.training_cutoff as string | undefined;
  const scoreline = result.metadata?.scoreline_model as string | undefined;
  const available = scoreline !== "unavailable";

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
      {modelType && (
        <span className="bg-navy-700 border border-slate-700 px-2 py-1 rounded-full">{modelType}</span>
      )}
      {trainingCutoff && (
        <span className="bg-navy-700 border border-slate-700 px-2 py-1 rounded-full">
          Trained to {trainingCutoff}
        </span>
      )}
      <span className="flex items-center gap-1 bg-navy-700 border border-slate-700 px-2 py-1 rounded-full">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${available ? "bg-pitch-400" : "bg-red-500"}`} />
        Scoreline model {available ? "active" : "inactive"}
      </span>
      <span className="bg-navy-700 border border-slate-700 px-2 py-1 rounded-full">
        {new Date().toLocaleTimeString()}
      </span>
    </div>
  );
}
