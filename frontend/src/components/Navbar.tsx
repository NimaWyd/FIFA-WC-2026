"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bars3Icon, XMarkIcon } from "@heroicons/react/24/solid";

const NAV_LINKS = [
  { label: "Groups",   href: "/groups" },
  { label: "Predict",  href: "/predict" },
  { label: "Simulate", href: "/simulate" },
  { label: "Teams",    href: "/teams" },
  { label: "About",    href: "/about" },
] as const;

export default function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

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
      <div className="max-w-7xl mx-auto px-6 md:px-14 flex items-center justify-between h-14">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 flex-shrink-0 group"
          aria-label="World Cup 26 home"
        >
          <div className="w-[22px] h-[22px] bg-pitch-400 rounded-[3px] rotate-45 group-hover:bg-pitch-300 transition-colors" />
          <span
            className={`font-anton text-[18px] tracking-[0.06em] ${
              isHome ? "text-[#f0ece2]" : "text-white"
            }`}
          >
            WC PREDICTOR 26
          </span>
        </Link>

        {/* Desktop links */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
          {NAV_LINKS.map(({ label, href }) => {
            const active = isActive(href);
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
                {label}
                {active && (
                  <span className="absolute bottom-0.5 left-4 right-4 h-[2px] rounded-full bg-pitch-400" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Mobile hamburger */}
        <button
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          className={`md:hidden p-2 rounded-md transition-colors ${
            isHome
              ? "text-[rgba(240,236,226,0.65)] hover:text-[#f0ece2] hover:bg-white/[0.06]"
              : "text-slate-400 hover:text-white hover:bg-navy-800"
          }`}
        >
          {open ? <XMarkIcon className="h-5 w-5" /> : <Bars3Icon className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile drawer */}
      {open && (
        <nav
          aria-label="Mobile navigation"
          className={`md:hidden border-t flex flex-col ${
            isHome
              ? "border-white/[0.06] bg-navy-900/80 backdrop-blur-md"
              : "border-navy-700 bg-navy-900"
          }`}
        >
          {NAV_LINKS.map(({ label, href }) => {
            const active = isActive(href);
            return (
              <Link
                key={label}
                href={href}
                onClick={() => setOpen(false)}
                className={`px-6 py-4 text-sm font-semibold uppercase tracking-wider border-b border-white/[0.04] flex items-center justify-between transition-colors ${
                  active
                    ? "text-white"
                    : isHome
                    ? "text-[rgba(240,236,226,0.55)] hover:text-[#f0ece2]"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {label}
                {active && (
                  <span className="w-1.5 h-1.5 rounded-full bg-pitch-400 flex-shrink-0" />
                )}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
