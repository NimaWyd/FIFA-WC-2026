import LandingHero from "@/components/LandingHero";
import TournamentCountdown from "@/components/TournamentCountdown";
import QuickPredict from "@/components/QuickPredict";
import BoldPredictions from "@/components/BoldPredictions";
import TitleContenders from "@/components/TitleContenders";

export default function Home() {
  return (
    <main className="min-h-screen bg-navy-900">
      <LandingHero />
      <TournamentCountdown />
      <QuickPredict />
      <BoldPredictions />
      <TitleContenders />
    </main>
  );
}
