"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const TARGET = new Date("2026-06-11T18:00:00Z");

function getTimeLeft() {
  const diff = TARGET.getTime() - Date.now();
  if (diff <= 0) return null;
  const totalSeconds = Math.floor(diff / 1000);
  return {
    days: Math.floor(totalSeconds / 86400),
    hours: Math.floor((totalSeconds % 86400) / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
  };
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

function DigitBlock({
  value,
  label,
  accent = false,
}: {
  value: string;
  label: string;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative overflow-hidden">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={value}
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 20, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className={`block font-anton tabular-nums leading-none text-[72px] sm:text-[96px] md:text-[112px] lg:text-[128px] ${
              accent ? "text-pitch-400" : "text-[#f0ece2]"
            }`}
          >
            {value}
          </motion.span>
        </AnimatePresence>
      </div>
      <span className="font-jb text-[10px] sm:text-[11px] tracking-[0.22em] uppercase text-[rgba(240,236,226,0.4)]">
        {label}
      </span>
    </div>
  );
}

type TimeLeft = ReturnType<typeof getTimeLeft>;

export default function TournamentCountdown() {
  const [mounted, setMounted] = useState(false);
  const [timeLeft, setTimeLeft] = useState<TimeLeft>(null);

  useEffect(() => {
    setMounted(true);
    setTimeLeft(getTimeLeft());
    const id = setInterval(() => setTimeLeft(getTimeLeft()), 1000);
    return () => clearInterval(id);
  }, []);

  if (timeLeft === null && mounted) {
    return (
      <section className="relative w-full bg-navy-900 border-t border-white/[0.06] py-14 text-center overflow-hidden">
        <div className="inline-flex items-center gap-2 bg-pitch-400/10 border border-pitch-400/30 rounded-full px-5 py-2.5">
          <span className="w-1.5 h-1.5 rounded-full bg-pitch-400 animate-pulse" />
          <span className="font-jb text-[13px] tracking-[0.08em] text-pitch-400 uppercase">
            Tournament underway
          </span>
        </div>
      </section>
    );
  }

  const units = [
    { value: mounted ? pad(timeLeft!.days) : "00", label: "Days", accent: true },
    { value: mounted ? pad(timeLeft!.hours) : "00", label: "Hours", accent: false },
    { value: mounted ? pad(timeLeft!.minutes) : "00", label: "Mins", accent: false },
    { value: mounted ? pad(timeLeft!.seconds) : "00", label: "Secs", accent: false },
  ];

  return (
    <section className="relative w-full bg-navy-900 border-t border-white/[0.06] overflow-hidden">
      {/* Green radial glow from below */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 140%, rgba(34,160,82,0.22) 0%, transparent 60%)",
        }}
      />
      {/* Pitch stripes */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          background:
            "repeating-linear-gradient(90deg, transparent 0 80px, #fff 80px 81px)",
        }}
      />

      <div className="relative flex flex-col items-center py-14 md:py-18 px-6">
        {/* Heading */}
        <p className="font-jb text-[10px] sm:text-[11px] tracking-[0.26em] uppercase text-[rgba(240,236,226,0.38)] mb-10">
          ◆&nbsp;&nbsp;World Cup Kicks Off In
        </p>

        {/* Digits row */}
        <div className="flex items-start justify-center gap-2 sm:gap-4 md:gap-6">
          {units.map(({ value, label, accent }, i) => (
            <div key={label} className="flex items-start gap-2 sm:gap-4 md:gap-6">
              <DigitBlock value={value} label={label} accent={accent} />
              {i < units.length - 1 && (
                <span className="font-anton text-[48px] sm:text-[64px] md:text-[80px] text-[rgba(240,236,226,0.18)] leading-none mt-2 select-none">
                  :
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Subtitle */}
        <p className="font-jb text-[11px] tracking-[0.18em] uppercase text-[rgba(240,236,226,0.30)] mt-10">
          Jun 11&nbsp;&nbsp;·&nbsp;&nbsp;Mexico City&nbsp;&nbsp;·&nbsp;&nbsp;Opening Match
        </p>
      </div>

      {/* Bottom border accent */}
      <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-pitch-400/30 to-transparent" />
    </section>
  );
}
