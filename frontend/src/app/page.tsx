import LandingHero from "@/components/LandingHero";
import TitleContenders from "@/components/TitleContenders";

export default function Home() {
  return (
    <main className="min-h-screen bg-navy-900">
      <LandingHero />
      <TitleContenders />
    </main>
  );
}
