"use client";

import { useEffect, useState } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { MapPinIcon, UsersIcon, ArrowTopRightOnSquareIcon } from "@heroicons/react/24/outline";
import { WC2026_STADIUMS } from "@/lib/wc2026Stadiums";

/* Counts up from 0 to `target` on mount */
function AnimatedCount({ value }: { value: number }) {
  const count = useMotionValue(0);
  const display = useTransform(count, (v) =>
    Math.floor(v).toLocaleString("en-US"),
  );
  useEffect(() => {
    const ctrl = animate(count, value, { duration: 1.6, delay: 0.55, ease: "easeOut" });
    return ctrl.stop;
  }, [value, count]);
  return <motion.span>{display}</motion.span>;
}

function SurfaceBadge({ surface }: { surface: string }) {
  const isGrass = surface.toLowerCase().includes("grass");
  return (
    <div
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[11px] font-semibold ${
        isGrass
          ? "bg-pitch-500/20 border-pitch-500/40 text-pitch-300"
          : "bg-navy-900/70 border-navy-600/60 text-slate-300"
      }`}
    >
      <span>{isGrass ? "🌿" : "⬛"}</span>
      <span>{surface}</span>
    </div>
  );
}

interface Props {
  venueCity: string;
}

export default function StadiumCard({ venueCity }: Props) {
  const [imgError, setImgError] = useState(false);
  const stadium = WC2026_STADIUMS[venueCity];

  if (!stadium) return null;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-navy-600 bg-navy-800 group">
      {/* ── Left glow bar ───────────────────────────────────── */}
      <div className="absolute left-0 inset-y-0 w-px bg-gradient-to-b from-fifa-blue via-fifa-blue/40 to-transparent z-20 pointer-events-none" />
      <div className="absolute left-0 inset-y-0 w-8 bg-gradient-to-r from-fifa-blue/10 to-transparent z-20 pointer-events-none" />

      {/* ── Top shimmer ─────────────────────────────────────── */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-fifa-blue/70 to-transparent z-20 pointer-events-none" />

      {/* ══════════════ IMAGE ZONE ══════════════════════════════ */}
      <div className="relative h-56 sm:h-72 overflow-hidden">
        {/* Ken Burns: subtle zoom-out */}
        <motion.div
          className="absolute inset-0"
          initial={{ scale: 1.10 }}
          animate={{ scale: 1 }}
          transition={{ duration: 12, ease: "easeOut" }}
        >
          {!imgError ? (
            <img
              src={stadium.imageUrl}
              alt={stadium.name}
              className="absolute inset-0 w-full h-full object-cover"
              loading="lazy"
              onError={() => setImgError(true)}
            />
          ) : (
            /* Fallback: architectural grid pattern */
            <div className="absolute inset-0 bg-gradient-to-br from-navy-700 via-navy-800 to-navy-900">
              <svg className="absolute inset-0 w-full h-full opacity-[0.06]" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
                    <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#1a3fff" strokeWidth="0.8" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="font-anton text-navy-600 text-5xl tracking-widest opacity-40">
                  {stadium.name.split(" ").map((w) => w[0]).join("")}
                </span>
              </div>
            </div>
          )}
        </motion.div>

        {/* Shimmer sweep — fires once on mount */}
        <motion.div
          className="absolute inset-0 pointer-events-none z-10"
          style={{
            background:
              "linear-gradient(108deg, transparent 35%, rgba(255,255,255,0.07) 50%, transparent 65%)",
          }}
          initial={{ x: "-110%" }}
          animate={{ x: "210%" }}
          transition={{ duration: 1.6, delay: 0.25, ease: "easeInOut" }}
        />

        {/* Gradient layers */}
        {/* Heavy dark at bottom for text */}
        <div className="absolute inset-0 bg-gradient-to-t from-navy-900 via-navy-900/55 to-transparent" />
        {/* FIFA blue vignette top-left */}
        <div className="absolute inset-0 bg-gradient-to-br from-fifa-blue/25 via-transparent to-transparent" />
        {/* Subtle right edge dark */}
        <div className="absolute inset-0 bg-gradient-to-l from-navy-900/40 to-transparent" />

        {/* ── "MATCH VENUE" live badge ── */}
        <motion.div
          className="absolute top-4 left-5 z-10"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
        >
          <div className="flex items-center gap-2 bg-navy-900/80 backdrop-blur-sm border border-fifa-blue/50 px-3 py-1.5 rounded-full shadow-lg shadow-black/40">
            <span className="relative flex h-2 w-2 flex-shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-fifa-blue opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-fifa-blue" />
            </span>
            <span className="text-[10px] font-bold tracking-[0.28em] text-white uppercase">
              Match Venue
            </span>
          </div>
        </motion.div>

        {/* ── FIFA WC 2026 watermark top-right ── */}
        <motion.div
          className="absolute top-4 right-5 z-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.35 }}
        >
          <div className="flex items-center gap-1.5 bg-navy-900/50 backdrop-blur-sm border border-white/[0.08] px-2.5 py-1 rounded-full">
            <span className="text-[8px] font-bold tracking-[0.25em] text-white/40 uppercase">FIFA WC 2026</span>
          </div>
        </motion.div>

        {/* ── Diagonal decorative lines (top-right corner detail) ── */}
        <div className="absolute top-0 right-0 w-32 h-32 pointer-events-none z-10 overflow-hidden opacity-[0.06]">
          {[0, 12, 24, 36, 48].map((offset) => (
            <div
              key={offset}
              className="absolute border-t border-fifa-blue"
              style={{
                width: "200%",
                top: `${offset}px`,
                right: `-50%`,
                transform: "rotate(-45deg)",
                transformOrigin: "top right",
              }}
            />
          ))}
        </div>

        {/* ── Bottom overlay: stadium name ── */}
        <motion.div
          className="absolute bottom-0 left-0 right-0 z-10 px-5 pb-5 pt-20"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div
            className="font-anton text-3xl sm:text-4xl text-white leading-tight"
            style={{ textShadow: "0 0 40px rgba(26,63,255,0.5), 0 2px 8px rgba(0,0,0,0.8)" }}
          >
            {stadium.name}
          </div>
          <div className="flex items-center gap-1.5 mt-2">
            <MapPinIcon className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
            <span className="text-slate-400 text-xs tracking-wide">
              {stadium.city} &middot; {stadium.country}
            </span>
          </div>
        </motion.div>
      </div>

      {/* ── Gold shimmer divider ─────────────────────────────── */}
      <div className="h-px bg-gradient-to-r from-transparent via-gold-500/50 to-transparent" />

      {/* ══════════════ STATS STRIP ══════════════════════════════ */}
      <motion.div
        className="px-5 py-3.5 flex items-center justify-between gap-3"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.5 }}
      >
        {/* Capacity (animated counter) */}
        <div className="flex items-center gap-2 bg-navy-900/60 border border-navy-600/60 px-3 py-1.5 rounded-lg">
          <UsersIcon className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
          <span className="text-[11px] font-semibold text-slate-300 tabular-nums">
            <AnimatedCount value={stadium.capacity} />
            <span className="text-slate-500 ml-1">cap.</span>
          </span>
        </div>

        {/* Surface */}
        <SurfaceBadge surface={stadium.surface} />

        {/* Altitude — amber badge when above 1000 m */}
        {stadium.altitude_m >= 1000 ? (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border bg-amber-500/15 border-amber-500/40 text-amber-300">
            <span className="text-[11px]">⛰️</span>
            <span className="text-[11px] font-semibold tabular-nums">{stadium.altitude_m.toLocaleString()} m</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 bg-navy-900/60 border border-navy-600/60 px-3 py-1.5 rounded-lg">
            <span className="text-[11px] text-slate-500">↑</span>
            <span className="text-[11px] font-semibold text-slate-300 tabular-nums">{stadium.altitude_m} m</span>
          </div>
        )}

        {/* Host nation flag + Wikipedia link */}
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-navy-900/60 border border-navy-600/60">
            <span className="text-[11px]">
              {stadium.country === "USA" ? "🇺🇸" : stadium.country === "Mexico" ? "🇲🇽" : "🇨🇦"}
            </span>
            <span className="text-[11px] font-semibold text-slate-300">{stadium.country}</span>
          </div>
          <a
            href={stadium.wikipediaUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-900/60 border border-navy-600/60 text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
            title="View on Wikipedia"
          >
            <ArrowTopRightOnSquareIcon className="h-3.5 w-3.5" />
            <span className="text-[11px] font-semibold">Wiki</span>
          </a>
        </div>
      </motion.div>

      {/* ── Bottom shimmer ───────────────────────────────────── */}
      <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-navy-600/60 to-transparent pointer-events-none" />
    </div>
  );
}
