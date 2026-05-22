import type { Metadata, Viewport } from "next";
import { Inter, Anton, JetBrains_Mono } from "next/font/google";
import "flag-icons/css/flag-icons.min.css";
import "./globals.css";
import Navbar from "@/components/Navbar";
import MobileBottomNav from "@/components/MobileBottomNav";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const anton = Anton({ weight: "400", subsets: ["latin"], variable: "--font-anton" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jb",
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "FIFA WC 2026 Predictor",
  description: "AI-powered match predictions for FIFA World Cup 2026",
};

export const viewport: Viewport = {
  themeColor: "#090b14",
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.className} ${anton.variable} ${jetbrainsMono.variable} antialiased min-h-screen bg-navy-900`}
      >
        <Navbar />
        <div className="pb-[calc(64px+env(safe-area-inset-bottom))] md:pb-0">
          {children}
        </div>
        <MobileBottomNav />
      </body>
    </html>
  );
}
