import type { Metadata } from "next";
import AboutPage from "./AboutPage";

export const metadata: Metadata = {
  title: "About — FIFA WC 2026 Predictor",
  description: "How the AI prediction model works, accuracy metrics, and what each output means.",
};

export default function Page() {
  return <AboutPage />;
}
