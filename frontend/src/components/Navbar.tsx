"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { InformationCircleIcon, TrophyIcon } from "@heroicons/react/24/solid";

const NAV_LINKS = [
  { label: "Live",     href: "/live" },
  { label: "Groups",   href: "/groups" },
  { label: "Predict",  href: "/predict" },
  { label: "Simulate", href: "/simulate" },
  { label: "Teams",    href: "/teams" },
  { label: "About",    href: "/about" },
] as const;

export default function Navbar() {
  const pathname = usePathname();
  const isHome = pathname === "/";

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <header
      className={
        isHome
          ? "sticky top-0 z-50 border-b border-white/[0.06] bg-navy-900/50 backdrop-blur-md"
          : "sticky top-0 z-50 border-b border-navy-700 bg-navy-900/95 backdrop-blur-sm"
      }
    >
      <div className="w-full px-6 md:px-14 flex items-center justify-between h-14">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 flex-shrink-0 group"
          aria-label="World Cup 26 home"
        >
          <TrophyIcon className="w-5 h-5 text-pitch-400 group-hover:text-pitch-300 transition-colors flex-shrink-0" />
          <span
            className={`font-anton text-[18px] tracking-[0.06em] ${
              isHome ? "text-[#f0ece2]" : "text-white"
            }`}
          >
            World Cup 2026
          </span>
        </Link>

        {/* Desktop links */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
          {NAV_LINKS.map(({ label, href }) => {
            const active = isActive(href);
            const isLive = label === "Live";
            return (
              <Link
                key={label}
                href={href}
                className={`relative px-4 py-2 text-[13px] font-semibold tracking-[0.05em] uppercase rounded-md transition-colors ${
                  active
                    ? isHome
                      ? "text-[#f0ece2] bg-white/[0.08]"
                      : "text-white bg-navy-700"
                    : isHome
                    ? "text-[rgba(240,236,226,0.55)] hover:text-[#f0ece2] hover:bg-white/[0.05]"
                    : "text-slate-400 hover:text-white hover:bg-navy-800"
                }`}
              >
                <span className="flex items-center gap-1.5">
                  {isLive && (
                    <span className="relative flex h-2 w-2 shrink-0">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                    </span>
                  )}
                  {label}
                </span>
                {active && (
                  <span className="absolute bottom-0.5 left-4 right-4 h-[2px] rounded-full bg-pitch-400" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Mobile: About icon only (bottom nav handles the rest) */}
        <Link
          href="/about"
          aria-label="About"
          className={`md:hidden p-2 rounded-md transition-colors ${
            isActive("/about")
              ? "text-pitch-400"
              : isHome
              ? "text-[rgba(240,236,226,0.55)] hover:text-[#f0ece2]"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <InformationCircleIcon className="h-5 w-5" />
        </Link>
      </div>
    </header>
  );
}
