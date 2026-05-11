import type { Metadata } from "next";
import TeamsIndexPage from "./TeamsIndexPage";

export const metadata: Metadata = {
  title: "Teams — FIFA WC 2026 Predictor",
  description: "Browse all 48 qualified teams at the 2026 FIFA World Cup.",
};

export default function Page() {
  return <TeamsIndexPage />;
}
