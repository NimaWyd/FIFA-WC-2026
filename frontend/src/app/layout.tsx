import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "flag-icons/css/flag-icons.min.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FIFA WC 2026 Predictor",
  description: "AI-powered match predictions for FIFA World Cup 2026",
};

export const viewport: Viewport = {
  themeColor: "#0a0e1a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} antialiased min-h-screen bg-[#0a0e1a]`}>
        {children}
      </body>
    </html>
  );
}
