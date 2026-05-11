import type { Metadata } from "next";
import { Suspense } from "react";
import TeamProfilePage from "./TeamProfilePage";

interface Props {
  params: Promise<{ name: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { name } = await params;
  const team = decodeURIComponent(name);
  return {
    title: `${team} — FIFA WC 2026 Predictor`,
    description: `Team profile, group fixtures, and match predictions for ${team} at the 2026 FIFA World Cup.`,
  };
}

export default async function Page({ params }: Props) {
  const { name } = await params;
  return (
    <Suspense fallback={<div className="min-h-screen bg-navy-900" />}>
      <TeamProfilePage name={decodeURIComponent(name)} />
    </Suspense>
  );
}
