import type { PredictResponse } from "@/lib/types";

interface Props {
  result: PredictResponse;
}

export default function MetadataBadge({ result }: Props) {
  const modelType = result.metadata?.model_type as string | undefined;
  const trainingCutoff = result.metadata?.training_cutoff as string | undefined;
  const scoreline = result.metadata?.scoreline_model_status as string | undefined;
  const available = scoreline !== "unavailable";
  const predictionTs = result.metadata?.prediction_timestamp as string | undefined;

  const timeLabel = predictionTs
    ? new Date(predictionTs).toLocaleTimeString()
    : new Date().toLocaleTimeString();
  const timePrefix = predictionTs ? "Predicted at" : "Viewed at";

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
      {modelType && (
        <span className="bg-navy-700 border border-navy-600 px-2 py-1 rounded-full">{modelType}</span>
      )}
      {trainingCutoff && (
        <span className="bg-navy-700 border border-navy-600 px-2 py-1 rounded-full">
          Trained to {trainingCutoff}
        </span>
      )}
      <span className="flex items-center gap-1 bg-navy-700 border border-navy-600 px-2 py-1 rounded-full">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${available ? "bg-green-400" : "bg-red-500"}`} />
        Scoreline model {available ? "active" : "inactive"}
      </span>
      <span className="bg-navy-700 border border-navy-600 px-2 py-1 rounded-full">
        {timePrefix} {timeLabel}
      </span>
    </div>
  );
}
