import { Suspense } from "react";
import PredictPage from "./PredictPage";

export const metadata = {
  title: "Predict a Match — FIFA WC 2026 Predictor",
  description: "Pick any two teams and get an AI-powered outcome prediction for FIFA World Cup 2026.",
};

export default function Page() {
  return (
    <Suspense>
      <PredictPage />
    </Suspense>
  );
}
