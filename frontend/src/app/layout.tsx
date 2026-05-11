import type { Metadata, Viewport } from "next";
import { Inter, Anton, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import "flag-icons/css/flag-icons.min.css";
import Navbar from "@/components/Navbar";

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
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.className} ${anton.variable} ${jetbrainsMono.variable} antialiased min-h-screen bg-navy-900`}
      >
        <Navbar />
        {children}
      </body>
    </html>
  );
}
