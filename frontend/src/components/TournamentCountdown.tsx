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

function DigitBlock({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="bg-white/[0.06] border border-white/[0.10] rounded-[4px] px-3 py-2 min-w-[52px] flex items-center justify-center overflow-hidden">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={value}
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 10, opacity: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="font-anton text-[28px] leading-none text-[#f0ece2] tabular-nums"
          >
            {value}
          </motion.span>
        </AnimatePresence>
      </div>
      <span className="font-jb text-[10px] tracking-[0.12em] uppercase text-[rgba(240,236,226,0.4)]">
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

  // SSR + initial client render — hold space to avoid layout shift
  if (!mounted) {
    return <div className="h-[72px] mt-6 md:mt-7" aria-hidden />;
  }

  if (timeLeft === null) {
    return (
      <div className="inline-flex items-center gap-2 bg-pitch-400/10 border border-pitch-400/30 rounded-full px-4 py-2 mt-6 md:mt-7">
        <span className="w-1.5 h-1.5 rounded-full bg-pitch-400 animate-pulse" />
        <span className="font-jb text-[12px] tracking-[0.08em] text-pitch-400 uppercase">
          Tournament underway
        </span>
      </div>
    );
  }

  const units = [
    { value: pad(timeLeft.days), label: "Days" },
    { value: pad(timeLeft.hours), label: "Hours" },
    { value: pad(timeLeft.minutes), label: "Mins" },
    { value: pad(timeLeft.seconds), label: "Secs" },
  ];

  return (
    <div className="flex items-end gap-2.5 mt-6 md:mt-7">
      {units.map(({ value, label }, i) => (
        <div key={label} className="flex items-center gap-2.5">
          <DigitBlock value={value} label={label} />
          {i < units.length - 1 && (
            <span className="font-anton text-[20px] text-[rgba(240,236,226,0.25)] mb-5 select-none">
              :
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
