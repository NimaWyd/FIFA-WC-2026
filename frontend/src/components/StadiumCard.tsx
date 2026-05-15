"use client";

import { useState } from "react";
import { MapPinIcon, UsersIcon } from "@heroicons/react/24/outline";
import { WC2026_STADIUMS } from "@/lib/wc2026Stadiums";

interface Props {
  venueCity: string;
}

export default function StadiumCard({ venueCity }: Props) {
  const [imgError, setImgError] = useState(false);
  const stadium = WC2026_STADIUMS[venueCity];

  if (!stadium) return null;

  const capacity = stadium.capacity.toLocaleString("en-US");

  return (
    <div className="relative overflow-hidden rounded-2xl border border-navy-600 bg-navy-800">
      {/* Top shimmer */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-fifa-blue/40 to-transparent z-10" />

      {/* Stadium image */}
      <div className="relative h-48 sm:h-60 overflow-hidden">
        {!imgError ? (
          <img
            src={stadium.imageUrl}
            alt={stadium.name}
            className="absolute inset-0 w-full h-full object-cover"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          /* Fallback: styled gradient banner */
          <div className="absolute inset-0 bg-gradient-to-br from-navy-700 via-navy-800 to-navy-900">
            <div className="absolute inset-0 opacity-10"
              style={{
                backgroundImage: "repeating-linear-gradient(45deg, currentColor 0, currentColor 1px, transparent 0, transparent 50%)",
                backgroundSize: "12px 12px",
                color: "rgb(59,130,246)",
              }}
            />
          </div>
        )}

        {/* Gradient overlay: dark at bottom for text, subtle at top */}
        <div className="absolute inset-0 bg-gradient-to-t from-navy-900 via-navy-900/60 to-navy-900/10" />

        {/* Content overlay */}
        <div className="absolute inset-0 flex flex-col justify-between p-5 sm:p-6">
          {/* Top-left: venue label */}
          <div>
            <span className="inline-block text-[10px] font-bold tracking-[0.3em] text-fifa-blue uppercase bg-navy-900/50 backdrop-blur-sm px-2.5 py-1 rounded-full border border-fifa-blue/20">
              Match Venue
            </span>
          </div>

          {/* Bottom: stadium name + details */}
          <div className="flex items-end justify-between gap-4">
            <div className="min-w-0">
              <div className="font-anton text-2xl sm:text-3xl text-white leading-tight truncate">
                {stadium.name}
              </div>
              <div className="flex items-center gap-1.5 mt-1.5">
                <MapPinIcon className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                <span className="text-slate-400 text-xs truncate">
                  {stadium.city} · {stadium.country}
                </span>
              </div>
            </div>

            {/* Stats badges */}
            <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
              <div className="flex items-center gap-1.5 bg-navy-900/60 backdrop-blur-sm border border-navy-600/80 px-2.5 py-1 rounded-lg">
                <UsersIcon className="h-3 w-3 text-slate-500" />
                <span className="text-[11px] font-semibold text-slate-300 tabular-nums">{capacity}</span>
              </div>
              <div className="bg-navy-900/60 backdrop-blur-sm border border-navy-600/80 px-2.5 py-1 rounded-lg">
                <span className="text-[11px] font-semibold text-slate-300">{stadium.surface}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
